import av
import re
import concurrent.futures as concurrent_futures
import subprocess

# from capture_devices import devices
from json import dump as json_dump
from json import load as json_load
from typing import Union, Tuple, List
from abc import ABC, abstractmethod
from logging import getLogger
from time import sleep
from logging import getLogger
from datetime import datetime
from traceback import format_exc
from platform import system
from numpy import frombuffer

from .datamodel import FramePacket
from .datamodel import PeripheryDevice, CameraDevice

# ------------------- DEVICE UTILS ------------------- #

def get_all_devices_ffmpeg():
    """
        - load all devices from ffmpeg stdout
        - remove prefixes and suffixes
    """
    
    # Get list of input devices
    devices = subprocess.run(["ffmpeg", "-sources", "dshow"], capture_output=True, text=True).stdout
    
    names = [a[1:-1] for a in re.findall("\[.*\]", devices)]
    device_ids = [f"@{a[1:-2]}" for a in re.findall("\@.*\[", devices)]
    device_type =[a[3:-1] for a in re.findall("\].*\(.*.\)", devices)]
    
    return [PeripheryDevice(
        device_id=device_id,
        name=name,
        device_type=device_type
    ) for name, device_id, device_type in zip(names, device_ids, device_type)]

def save_periphery_devices_to_config(devices: List[PeripheryDevice], config_file: str = "./raw_devices.json"):
    with open(config_file, "w") as f:
        json_dump([device.model_dump() for device in devices], f)

def load_all_periphery_devices_from_config(config_file: str = "./configs/raw_devices.json") -> List[PeripheryDevice]:
    with open(config_file, "r") as f:
        return [CameraDevice(**device) for device in json_load(f)]

def load_all_camera_devices_from_config(config_file: str = "./configs/cameras_device_configs.json") -> List[CameraDevice]:
    with open(config_file, "r") as f:
        return [CameraDevice(**device) for device in json_load(f)]

# ------------------- BASE CLASS ------------------- #

class FFMPEGReader(ABC):
    def __init__(self, device: PeripheryDevice, logger_name: str):
        self.logger = getLogger(logger_name)
        
        self.device = device
        self.container = None
        self.stream = None
    
    def is_activ(self):
        return self.container is not None or self.stream is not None
    
    def stop(self):
        self.logger.info("Stopping reader ...")
        
        if self.container is not None:
            self.container.close()
            self.container = None
            self.stream = None
        self.is_active = False
        
        self.logger.info("Reader stopped!")
    
    @abstractmethod
    def start(self):
        
        self.logger.info(f"Starting reader ...")
        
        if self.is_activ():
            self.logger.warning(f"Trying to start a reader that has already been started, stopping and restarting ...")
            self.stop()
    
    @abstractmethod
    def read(self, timeout: float = 1):
        
        with concurrent_futures.ThreadPoolExecutor(max_workers=1) as executor:
            
            future = executor.submit(next, self.container.decode(self.stream))
            
            try:
                frame = future.result(timeout)
                return frame.to_ndarray()
            
            except concurrent_futures.TimeoutError:
                self.logger.warning("Timeout while reading frame ...")
                return None
            
            except StopIteration:
                self.logger.warning("No frame found ...")
                return None
            
            except Exception as e:
                self.logger.error(format_exc())
                self.stop()
                raise e


# ------------------- FFMPEG READERS ------------------- #

class CameraDeviceReader(FFMPEGReader):
    def __init__(self, camera: CameraDevice):
        
        super().__init__(
            device=camera,
            logger_name=f"{__class__.__name__}@{camera.device_id}")
        
    def start(self):
        
        super().start()
        
        try:
            # set container
            self.container = av.open(
                file=f'video={self.device.device_id}', 
                format='dshow',
                options={
                    'video_size': f'{self.device.width}x{self.device.height}', 
                    'framerate': f'{self.device.fps}'
                })
            
            # set video stream
            self.stream = self.container.streams.video[0]
        
        except Exception as e:
            self.stop()
            raise e
    
    def read(self, timeout: int = 1):
        
        start_read_dt = datetime.now()
        ret = super().read(timeout=timeout)
        end_read_dt = datetime.now()
        
        if ret is None:
            return None
        
        return FramePacket(
            device=self.device,
            frame=ret,
            start_read_dt=start_read_dt,
            end_read_dt=end_read_dt
        )


def start_audio_ffmpeg_container(device_id: str, sample_rate: int = 44100, channels: int = 2, bit_rate: int = 16):
    return av.open(
        file=f'audio={device_id}', 
        format='dshow',
        options={
            'sample_rate': f'{sample_rate}',
            'bit_rate': f'{bit_rate}',
            'channels': f'{channels}'
        })

# class CameraDeviceReader(DeviceReader):
#     def __init__(
#         self, 
#         camera: CameraDevice, 
#         max_consec_failures: int = 10, 
#         frame_transform: str = None):
        
#         super().__init__(logger_name=f"{__class__.__name__}@{camera.uuid}")
        
#         self.max_consec_failures = max_consec_failures
#         self.camera = camera
#         self.fail_counter = 0
        
#         # set backend and capture
#         self.capture = cv2.VideoCapture(self.camera.id, cv2Backends[system()])
        
#         # set capture parameters and test
#         set_fps = self.capture.set(cv2.CAP_PROP_FPS, self.camera.fps)
#         set_width = self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.camera.width)
#         set_height = self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.camera.height)
        
#         if not set_fps or not set_width or not set_height:
#             self.logger.error(f"inccorect set : set_fps = {set_fps}, set_width = {set_width}, set_height = {set_height} ...")
#             raise Exception("Failed to set camera parameters ...")
        
#         # define frame transform
#         if frame_transform == "ROTATE_90_CLOCKWISE":
#             self.frame_transform = lambda frame: rotate(frame, ROTATE_90_CLOCKWISE)
#         elif frame_transform == "ROTATE_90_COUNTERCLOCKWISE":
#             self.frame_transform = lambda frame: rotate(frame, ROTATE_90_COUNTERCLOCKWISE)
#         elif frame_transform == "ROTATE_180":
#             self.frame_transform = lambda frame: rotate(frame, ROTATE_180)
#         else:
#             self.frame_transform = lambda frame: frame
        
        
#         # initialize camera befor use
#         self.initialize()
        
#     def is_open(self):
#         return self.capture.isOpened()
    
#     def initialize(self):
#         super().initialize()
        
#         try:
#             open_attempts = 0
            
#             while True:
                
#                 assert open_attempts < self.max_consec_failures, f"{self.camera.uuid} :: Failed to open capture after {open_attempts} attempts"
                
#                 self.logger.info(f"{self.camera.uuid} :: Attempting to open capture {open_attempts}/{self.max_consec_failures} ...")
                
#                 # try read frames
#                 if not self.is_open():
                    
#                     self.logger.warning(f"{self.camera.uuid} :: Capture not open ...")
                    
#                     self.capture.open(self.camera.id, CV2_BACKENDS.get(system(), cv2.CAP_ANY))
#                     sleep(0.33)
#                     open_attempts += 1
#                     continue
                
#                 read_attempts = 0
#                 for _ in range(self.max_consec_failures):
#                     self.logger.info(f"{self.camera.uuid} :: Capture open, try reading {read_attempts}/{self.max_consec_failures} ...")
                    
#                     ok, _ = self.capture.read()
#                     if ok:
#                         self.logger.info(f"{self.camera.uuid} :: Camera initialization successful!")
#                         return
#                     read_attempts += 1
                
            
#         except:
#             raise
        
#     def stop(self):
#         super().stop()
#         self.capture.release()
#         self.logger.info(f"{self.camera.uuid} :: Capture stoped")
        
#     def read_(self):
        
#         try:
#             # try read frame and define camera read time
#             ok, frame = self.capture.read()
            
#             # count incorrect reads
#             if not ok:
#                 # log warning and increment fail counter
#                 self.logger.warning(f"{self.camera.uuid} :: reader issue for {self.fail_counter}/{self.max_consec_failures} frames ...")
#                 self.fail_counter += 1
#                 # close and throw if too many failures
#                 assert self.fail_counter < self.max_consec_failures, f"{self.camera.uuid} :: no valid frame found after {self.fail_counter} consecutive attempts"
                
#                 sleep(0.33)
#                 return None
            
#             # successfull read, reset fail counter and return
#             self.fail_counter = 0
#             frame = self.frame_transform(frame)
#             return frame
        
#         except KeyboardInterrupt:
#             self.logger.info(f"KeyboardInterrupt ...")
#             self.stop()
#             raise
#         except:
#             self.logger.error(format_exc())
#             self.stop()
#             raise
        
#     def read(self):
#         frames, start_read_dt, end_read_dt = super().read()
#         return CameraFramePacket(device=self.camera, frames=frames, start_read_dt=start_read_dt, end_read_dt=end_read_dt)


# # ------------------- AudioIO ------------------- #

# class AudioInputDevice(DeviceReader):
#     def __init__(self, audio_device: AudioDevice, max_consec_failures: int = 10):
#         super().__init__()
        
#         self.audio_device = audio_device
#         self.max_consec_failures = max_consec_failures
        
#         # create pyaudio instance
#         self.audio = PyAudio()
#         self.stream = self.audio.open(
#                     start=False,
#                     format=paInt16, 
#                     output=audio_device.type == "output",
#                     input=audio_device.type == "input",
#                     input_device_index=audio_device.id,
#                     channels=audio_device.channels,
#                     rate=audio_device.sample_rate,
#                     frames_per_buffer=audio_device.frames_per_buffer)
        
#         self.initialize()
        
#     @classmethod
#     def list_devices(cls):
#         audio = PyAudio()
#         for i in range(audio.get_device_count()):
#             print(audio.get_device_info_by_index(i))
#         audio.terminate()
        
#     def initialize(self):
#         super().initialize()
        
        
#         '''
#             multiple attepmts to start a stream
            
#         '''
#         try:
            
#             start_attempts = 0
            
#             while start_attempts < self.max_consec_failures:
                
#                 self.logger.info(f"Attempting to start audio stream {start_attempts}/{self.max_consec_failures} ...")
                
#                 self.stream.start_stream()
                
#                 if not self.stream.is_active():
#                     self.logger.info(f"Failed to start audio stream ({start_attempts}/{self.max_consec_failures}) ...")
                    
#                     if start_attempts >= self.max_consec_failures:
#                         self.logger.error(f"Failed to start audio stream after {start_attempts} attempts ...")
#                         raise Exception("Failed to start audio stream ...")
                    
#                     start_attempts += 1
#                     sleep(0.33)
#                     continue
                
#                 self.logger.info(f"Audio stream initialized successfully ...")
#                 # self.stream.stop_stream()
#                 break
#         except:
#             raise
        
#     def is_open(self):
#         return not self.stream.is_stopped()
    
#     # def start(self):
#     #     super().start()
#     #     try:
#     #         self.stream.start_stream()
#     #         self.logger.info(f"Audio stream started ...")
#     #     except Exception as e:
#     #         raise e
        
#     def stop(self):
#         super().stop()
#         try:
#             self.stream.stop_stream()
#             self.logger.info(f"Audio stream stopped ...")
#         except Exception as e:
#             raise e
        
#     def read_(self):
#         try:
#             # read audio frames
#             frames = frombuffer(self.stream.read(self.audio_device.frames_per_buffer), dtype="int16")
            
#             # count incorrect reads
#             if frames is None or len(frames) == 0:
#                 # log warning and increment fail counter
#                 self.logger.warning(f"{self.camera.uuid} :: reader issue for {self.fail_counter}/{self.max_consec_failures} frames ...")
#                 self.fail_counter += 1
#                 # close and throw if too many failures
#                 assert self.fail_counter < self.max_consec_failures, f"{self.camera.uuid} :: no valid frame found after {self.fail_counter} consecutive attempts"
                
#                 sleep(0.33)
#                 return None
            
#             # successfull read, reset fail counter and return
#             self.fail_counter = 0
#             return frames
        
#         except KeyboardInterrupt:
#             self.logger.info(f"KeyboardInterrupt ...")
#             self.stop()
#             raise
#         except:
#             self.logger.error(format_exc())
#             self.stop()
#             raise
        
#     def read(self):
#         frames, start_read_dt, end_read_dt = super().read()
#         return AudioFramePacket(device=self.audio_device, frames=frames, start_read_dt=start_read_dt, end_read_dt=end_read_dt)
        