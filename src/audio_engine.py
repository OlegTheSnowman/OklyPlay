import numpy as np
import soundfile as sf
import sounddevice as sd


def _pitch_shift(data: np.ndarray, semitones: float) -> np.ndarray:
    """Shift pitch by semitones without changing duration using a double-resample technique."""
    if semitones == 0.0:
        return data
    N = len(data)
    if N == 0:
        return data
    pitch_factor = 2.0 ** (semitones / 12.0)
    N_shifted = max(1, int(round(N / pitch_factor)))
    t_in = np.arange(N, dtype=np.float64)
    t_out = np.linspace(0.0, N - 1, N_shifted, dtype=np.float64)
    shifted = np.column_stack((
        np.atleast_1d(np.interp(t_out, t_in, data[:, 0])),
        np.atleast_1d(np.interp(t_out, t_in, data[:, 1])),
    ))
    # Resample back to original length to restore duration
    t_in2 = np.arange(N_shifted, dtype=np.float64)
    t_out2 = np.linspace(0.0, N_shifted - 1, N, dtype=np.float64)
    return np.column_stack((
        np.atleast_1d(np.interp(t_out2, t_in2, shifted[:, 0])),
        np.atleast_1d(np.interp(t_out2, t_in2, shifted[:, 1])),
    )).astype(np.float32)


class LoadedSound:
    """Represents a preloaded audio file in memory resampled to output samplerate."""
    def __init__(self, filepath, target_samplerate):
        self.filepath = filepath
        self.target_samplerate = target_samplerate
        
        # Read the audio file
        data, samplerate = sf.read(filepath, dtype='float32')
        
        # Convert mono/multichannel to stereo (shape N, 2)
        if len(data.shape) == 1:
            data = np.column_stack((data, data))
        elif data.shape[1] == 1:
            data = np.column_stack((data[:, 0], data[:, 0]))
        elif data.shape[1] > 2:
            data = data[:, :2]
            
        # Resample to target sample rate using linear interpolation if needed
        if samplerate != target_samplerate:
            duration = len(data) / samplerate
            num_output_samples = int(duration * target_samplerate)
            t_in = np.linspace(0, duration, len(data), endpoint=False)
            t_out = np.linspace(0, duration, num_output_samples, endpoint=False)
            
            left = np.interp(t_out, t_in, data[:, 0])
            right = np.interp(t_out, t_in, data[:, 1])
            data = np.column_stack((left, right))
            samplerate = target_samplerate
            
        self.data = data.astype(np.float32)
        self.samplerate = samplerate
        self._audio_cache: dict = {(0.0, 1.0): self.data}

    def get_data_for_pitch_and_speed(self, pitch_semitones: float, speed: float) -> np.ndarray:
        """Returns audio data with pitch shift and speed applied.

        Pitch is shifted first (duration-preserving double-resample), then speed
        resampling is applied on top (changes duration, like tape speed).
        """
        pitch_key = round(float(pitch_semitones) * 2) / 2  # snap to nearest 0.5 semitone
        speed_key = round(float(speed), 2)
        if speed_key <= 0.01:
            speed_key = 1.0

        cache_key = (pitch_key, speed_key)
        if cache_key not in self._audio_cache:
            pitched = _pitch_shift(self.data, pitch_key)
            if speed_key == 1.0:
                result = pitched
            else:
                N = len(pitched)
                N_new = int(N / speed_key)
                if N_new <= 0:
                    result = np.zeros((0, 2), dtype=np.float32)
                else:
                    t_in = np.arange(N)
                    t_out = np.linspace(0, N - 1, N_new)
                    result = np.column_stack((
                        np.interp(t_out, t_in, pitched[:, 0]),
                        np.interp(t_out, t_in, pitched[:, 1]),
                    )).astype(np.float32)
            self._audio_cache[cache_key] = result

        return self._audio_cache[cache_key]


class Channel:
    """Represents a single active sound playback instance with fade capabilities."""
    def __init__(self, sound_data, volume, fade_in_ms, fade_out_ms, loop, bus_id, sample_rate, sound_name=""):
        self.audio_data = sound_data
        self.target_volume = float(volume)
        self.loop = bool(loop)
        self.bus_id = bus_id
        self.sample_rate = sample_rate
        self.sound_name = sound_name
        
        self.position = 0
        self.is_done = False
        
        # Fade-in parameters
        self._fade_in_samples = int(fade_in_ms * sample_rate / 1000)
        self._samples_played = 0
        
        # Fade-out parameters
        self._fading_out = False
        self._fade_out_samples = int(fade_out_ms * sample_rate / 1000)
        self._fade_out_elapsed = 0
        self._fade_out_start_vol = 0.0

    def start_fade_out(self, fade_out_ms=None):
        """Triggers a linear fade-out of the channel."""
        if self._fading_out or self.is_done:
            return
            
        if fade_out_ms is not None:
            self._fade_out_samples = int(fade_out_ms * self.sample_rate / 1000)
            
        # Calculate the starting volume for the fade-out (taking current fade-in into account)
        current_vol = self.target_volume
        if self._fade_in_samples > 0 and self._samples_played < self._fade_in_samples:
            current_vol *= (self._samples_played / self._fade_in_samples)
            
        self._fade_out_start_vol = current_vol
        self._fading_out = True
        self._fade_out_elapsed = 0
        
        if self._fade_out_samples <= 0:
            self.is_done = True

    def render(self, num_frames):
        """Renders up to num_frames of audio, applying volume envelopes and fades."""
        if self.is_done:
            return np.zeros((num_frames, 2), dtype=np.float32)
            
        data_len = len(self.audio_data)
        if data_len == 0:
            self.is_done = True
            return np.zeros((num_frames, 2), dtype=np.float32)
            
        # Read frames, looping if enabled
        chunk = np.zeros((num_frames, 2), dtype=np.float32)
        frames_written = 0
        
        while frames_written < num_frames:
            remaining = data_len - self.position
            if remaining <= 0:
                if self.loop and not self._fading_out:
                    self.position = 0
                    remaining = data_len
                else:
                    break
                    
            n = min(num_frames - frames_written, remaining)
            chunk[frames_written : frames_written + n] = self.audio_data[self.position : self.position + n]
            self.position += n
            frames_written += n
            
        if frames_written == 0:
            self.is_done = True
            return chunk
            
        # Build volume envelope vectorially
        envelope = np.ones(frames_written, dtype=np.float32)
        
        # 1) Fade-in ramp
        if self._fade_in_samples > 0 and self._samples_played < self._fade_in_samples:
            indices = np.arange(self._samples_played, self._samples_played + frames_written, dtype=np.float32)
            in_fade = indices < self._fade_in_samples
            envelope[in_fade] = indices[in_fade] / self._fade_in_samples
            
        # 2) Target volume scale
        envelope *= self.target_volume
        
        # 3) Fade-out ramp override
        if self._fading_out:
            if self._fade_out_samples > 0:
                fo_indices = np.arange(self._fade_out_elapsed, self._fade_out_elapsed + frames_written, dtype=np.float32)
                active = fo_indices < self._fade_out_samples
                
                fade_curve = np.zeros(frames_written, dtype=np.float32)
                fade_curve[active] = 1.0 - fo_indices[active] / self._fade_out_samples
                envelope = self._fade_out_start_vol * fade_curve
                
                self._fade_out_elapsed += frames_written
                if self._fade_out_elapsed >= self._fade_out_samples:
                    self.is_done = True
            else:
                self.is_done = True
                return np.zeros((num_frames, 2), dtype=np.float32)
                
        self._samples_played += frames_written
        
        # Apply envelope
        result = np.zeros((num_frames, 2), dtype=np.float32)
        result[:frames_written] = chunk[:frames_written] * envelope[:, np.newaxis]
        return result


class AudioEngine:
    """Manager for real-time stereo mixing and playback using sounddevice."""
    def __init__(self, sample_rate=44100):
        self.sample_rate = sample_rate
        self._device_index = None
        self._stream = None
        self._active_channels = []  # Thread-safe copy-on-write channel list
        self._loaded_sounds = {}    # Cache path -> LoadedSound
        self._master_volume = 1.0
        self._bus_volumes = {}      # bus_id -> volume float
        self._bus_duck_factors = {} # bus_id -> duck factor float (0.0 - 1.0)
        self._bus_duckable = {}     # bus_id -> bool
        self._bus_current_duck_factors = {} # bus_id -> transient current duck factor
        
        self._open_stream()

    def _open_stream(self):
        """Close existing stream and open a new one on the current device."""
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
            
        try:
            self._stream = sd.OutputStream(
                device=self._device_index,
                channels=2,
                samplerate=self.sample_rate,
                callback=self._callback,
                dtype='float32'
            )
            self._stream.start()
        except Exception as e:
            print(f"Failed to open audio stream on device {self._device_index}: {e}")
            if self._device_index is not None:
                print("Attempting fallback to default output device...")
                self._device_index = None
                self._open_stream()
            else:
                raise e

    def _callback(self, outdata, frames, time_info, status):
        """Sounddevice stream callback running in C-level audio thread."""
        outdata.fill(0.0)
        
        # Take a snapshot of the active channels to avoid lock contention
        channels_snapshot = self._active_channels
        
        # Determine target duck factors for all buses first
        target_ducks = {}
        for bus_id in list(self._bus_volumes.keys()):
            target_duck = 1.0
            if self._bus_duckable.get(bus_id, False):
                for other_ch in channels_snapshot:
                    if other_ch.is_done:
                        continue
                    if other_ch.bus_id != bus_id:
                        factor = self._bus_duck_factors.get(other_ch.bus_id, 1.0)
                        if factor < target_duck:
                            target_duck = factor
            target_ducks[bus_id] = target_duck

        # Compute ducking envelope for each bus
        bus_duck_envelopes = {}
        for bus_id, target_duck in target_ducks.items():
            d_start = self._bus_current_duck_factors.get(bus_id, 1.0)
            if target_duck < d_start:
                # Attack: ramp down to target_duck (e.g. 150ms)
                max_change = frames / (0.15 * self.sample_rate)
                d_end = max(target_duck, d_start - max_change)
            elif target_duck > d_start:
                # Release: ramp up to target_duck (e.g. 400ms)
                max_change = frames / (0.4 * self.sample_rate)
                d_end = min(target_duck, d_start + max_change)
            else:
                d_end = target_duck
            
            self._bus_current_duck_factors[bus_id] = d_end
            
            if d_start == d_end == 1.0:
                bus_duck_envelopes[bus_id] = None
            else:
                bus_duck_envelopes[bus_id] = np.linspace(d_start, d_end, frames, dtype=np.float32)

        for ch in channels_snapshot:
            if ch.is_done:
                continue
            rendered = ch.render(frames)
            bus_vol = self._bus_volumes.get(ch.bus_id, 1.0)
            
            # Apply ducking envelope if present
            envelope = bus_duck_envelopes.get(ch.bus_id)
            if envelope is not None:
                n = len(rendered)
                rendered = rendered * envelope[:n, np.newaxis]
                
            outdata[:len(rendered)] += rendered * (bus_vol * self._master_volume)
            
        np.clip(outdata, -1.0, 1.0, out=outdata)

    def play(self, filepath, scenario, bus_id, bus_mode, exclusive_bus_ids=None, crossfade_ms=500, sound_name=""):
        """Plays a sound on a bus with a given scenario preset."""
        if filepath not in self._loaded_sounds:
            self._loaded_sounds[filepath] = LoadedSound(filepath, self.sample_rate)
            
        loaded_sound = self._loaded_sounds[filepath]
        pitch_semitones = scenario.get('pitch_semitones', 0.0)
        speed = scenario.get('speed', 1.0)
        audio_data = loaded_sound.get_data_for_pitch_and_speed(pitch_semitones, speed)
        
        fade_in_ms = scenario.get('fade_in_ms', 0)
        if bus_mode == 'exclusive' and fade_in_ms == 0:
            fade_in_ms = crossfade_ms
        fade_out_ms = scenario.get('fade_out_ms', 0)
        
        # Exclusive bus behavior: crossfade other channels on exclusive buses (or same bus if exclusive_bus_ids not provided)
        if bus_mode == 'exclusive':
            if exclusive_bus_ids is not None:
                for ch in self._active_channels:
                    if ch.bus_id in exclusive_bus_ids and not ch._fading_out:
                        ch.start_fade_out(crossfade_ms)
            else:
                for ch in self._active_channels:
                    if ch.bus_id == bus_id and not ch._fading_out:
                        ch.start_fade_out(fade_in_ms)
                    
        new_channel = Channel(
            sound_data=audio_data,
            volume=scenario.get('volume', 1.0),
            fade_in_ms=fade_in_ms,
            fade_out_ms=fade_out_ms,
            loop=scenario.get('loop', False),
            bus_id=bus_id,
            sample_rate=self.sample_rate,
            sound_name=sound_name
        )
        
        # Copy-on-write list assignment
        self._active_channels = self._active_channels + [new_channel]
        return new_channel

    def stop_channel(self, channel, fade_out_ms=None):
        """Stops a specific channel with optional fade-out."""
        channel.start_fade_out(fade_out_ms)

    def stop_bus(self, bus_id, fade_out_ms=None):
        """Stops all active channels on a specific bus with optional fade-out."""
        for ch in self._active_channels:
            if ch.bus_id == bus_id:
                ch.start_fade_out(fade_out_ms)

    def stop_all(self, fade_out_ms=None):
        """Stops all active channels across all buses with optional fade-out."""
        for ch in self._active_channels:
            ch.start_fade_out(fade_out_ms)

    def set_master_volume(self, volume):
        """Sets the master volume (0.0 to 1.0)."""
        self._master_volume = max(0.0, min(1.0, float(volume)))

    def set_bus_volume(self, bus_id, volume):
        """Sets the volume multiplier for a specific bus."""
        self._bus_volumes[bus_id] = max(0.0, min(1.0, float(volume)))

    def set_bus_duck_factor(self, bus_id, duck_factor):
        """Sets the duck factor multiplier for a specific bus (0.0 to 1.0)."""
        self._bus_duck_factors[bus_id] = max(0.0, min(1.0, float(duck_factor)))

    def set_bus_duckable(self, bus_id, duckable):
        """Sets whether a specific bus is subject to ducking."""
        self._bus_duckable[bus_id] = bool(duckable)

    def clear_buses_config(self):
        """Clears all bus volume and ducking settings."""
        self._bus_volumes.clear()
        self._bus_duck_factors.clear()
        self._bus_duckable.clear()
        self._bus_current_duck_factors.clear()

    def get_active_channels_count(self):
        """Returns the number of active, non-completed channels."""
        return sum(1 for ch in self._active_channels if not ch.is_done)

    def cleanup_done_channels(self):
        """Filters out finished channels and returns them. Call from main thread periodically."""
        done = [ch for ch in self._active_channels if ch.is_done]
        if done:
            self._active_channels = [ch for ch in self._active_channels if not ch.is_done]
        return done

    def get_output_devices(self):
        """Returns a list of tuples (device_index, device_name) for output devices."""
        try:
            devices = sd.query_devices()
            return [(i, d['name']) for i, d in enumerate(devices) if d.get('max_output_channels', 0) > 0]
        except Exception as e:
            print(f"Error querying audio devices: {e}")
            return []

    def set_output_device(self, device_index):
        """Closes the current stream and opens a new one on the specified device index."""
        self.stop_all(fade_out_ms=0)
        self.cleanup_done_channels()
        self._device_index = device_index
        self._open_stream()
        
    def close(self):
        """Safely stops and closes the audio stream."""
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
