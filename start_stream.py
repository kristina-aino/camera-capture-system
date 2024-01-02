from logging import getLogger, basicConfig
from traceback import format_exc
import argparse

# ---------------------------------------------------------------------

AP = argparse.ArgumentParser()
AP.add_argument("-cc", "--cameras_config", type=str, default="./cameras_configs.json", help="path to input configuration file")
AP.add_argument("-hn", "--host_name", type=str, default="127.0.0.1", help="host name or ip of the server")
AP.add_argument("-p", "--ports", nargs="+", default=[10000, 10001], help="port to opsn zmq socket on")
AP.add_argument("-ll", "--logging_level", type=str, default="info", help="logging level", choices=["debug", "warning", "error"])
AP.add_argument("-pm", "--publishing_mode", type=str, default="ALL_AVAILABLE", help="publishing mode", choices=["ALL_AVAILABLE"])
AP.add_argument("-mcrf", "--max_consec_reader_failures", type=int, default=10, help="max consecutive reader failures")
ARGS = AP.parse_args()

# ---------------------------------------------------------------------

basicConfig(level=ARGS.logging_level.upper())
logger = getLogger(__name__)

# ---------------------------------------------------------------------

# Setp 1: read camera configurations for all cameras
from camera_capture_system.core import load_all_cameras_from_config, MultiCameraCaptureAndPublish

try:
    cameras = load_all_cameras_from_config(ARGS.cameras_config)
    pccp = MultiCameraCaptureAndPublish(
        cameras=cameras,
        host_name=ARGS.host_name,
        ports=ARGS.ports,
        PUBLISHING_MODE=ARGS.publishing_mode,
        max_consec_reader_failures=ARGS.max_consec_reader_failures)
    
    pccp.start()
except KeyboardInterrupt:
    logger.info(f"KeyboardInterrupt ...")
except:
    logger.error(format_exc())
    raise