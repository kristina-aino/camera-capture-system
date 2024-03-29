import argparse
import logging
import argparse

# ---------------------------------------------------------------------

AP = argparse.ArgumentParser()
AP.add_argument("-cc", "--cameras_config", type=str, default="./cameras_configs.json", help="path to input configuration file")
AP.add_argument("-hn", "--host_name", type=str, default="127.0.0.1", help="host name or ip of the server")

AP.add_argument("-op", "--output_path", type=str, required=True, help="output path")
AP.add_argument("--fps", type=int, default=30, help="fps of the output video (usually the same as the cameras)")
AP.add_argument("--seconds", type=int, default=10, help="number of seconds in the output video")

AP.add_argument("-ll", "--logging_level", type=str, default="info", help="logging level", choices=["debug", "warning", "error"])
ARGS = AP.parse_args()

# ---------------------------------------------------------------------

logging.basicConfig(level=ARGS.logging_level.upper())

# ---------------------------------------------------------------------

from camera_capture_system.core import load_all_cameras_from_config, MultiCaptureSubscriber
from camera_capture_system.fileIO import save_captures_as_videos
from camera_capture_system.datamodel import VideoParameters

if __name__ == "__main__":
    cameras = load_all_cameras_from_config(ARGS.cameras_config)
    
    mcsb = MultiCaptureSubscriber(cameras=cameras, host_name=ARGS.host_name, q_size=1)
    video_params = VideoParameters(save_path=ARGS.output_path, fps=ARGS.fps, seconds=ARGS.seconds, codec="mp4v")

    save_captures_as_videos(mcsb, video_params)
