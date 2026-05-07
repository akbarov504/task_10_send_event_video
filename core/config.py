import os

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(ROOT_DIR)
PARENT_DIR = os.path.dirname(BASE_DIR)

TASK_7_VERTUAL_PATH = os.path.join(PARENT_DIR, "task_7_vertual")
LOCAL_PATH = os.path.join(TASK_7_VERTUAL_PATH, 'records/')
DB_PATH = os.path.join(TASK_7_VERTUAL_PATH, 'adas_dms.db')

MODEL_PATH = os.path.join(PARENT_DIR, 'models/')
SOUND_PATH = os.path.join(BASE_DIR, 'sounds/')
REF_IMAGES = os.path.join(BASE_DIR, 'ref_images/')

# api and token config
API_BASE_EVENT = 'https://dev-gw.tracksafe365.com/services/glssafety/api'
API_BASE_STREAM = 'https://dev-gw.tracksafe365.com/services/glsstream/api'
TOKEN_REFRESH_MARGIN = 300  # seconds (5 minutes before expiry)
TOKEN_FILE_PATH = os.path.join(BASE_DIR, 'token_info.json')


# Camera config
CAMERA_TYPE = 'usb' # or 'csi'
CAMERA_INDEX_INNER = '/dev/v4l/by-path/platform-xhci-hcd.0.auto-usb-0:1.3:1.0-video-index0'
CAMERA_INDEX_FRONT = '/dev/v4l/by-path/platform-xhci-hcd.10.auto-usb-0:1:1.0-video-index0'

CAMERA_PATH_INNER = 'usb-xhci-hcd.10.auto-1.2'
CAMERA_PATH_FRONT = 'usb-xhci-hcd.0.auto-1.3'
AUDIO_DEVICE_INNER = 3
AUDIO_DEVICE_FRONT = 4
AUDIO_DEVICE_NAME = 'USB' #'Arducam USB Camera'

# Model paths
INNER_MODEL = 'inner_cam_rknn_model'
FRONT_MODEL = 'front_cam_rknn_model'
LANE_MODEL = 'lane_detection_rknn_model'


# Queue and retry
UPLOAD_RETRY_INTERVAL = 60  # seconds
QUEUE_SIZE = 50

# Video upload settings
UPLOAD_BATCH_SIZE = 4          # videos per upload cycle
UPLOAD_CYCLE_INTERVAL = 10     # seconds between upload cycles
MIN_VIDEO_AGE_SECONDS = 2      # wait N seconds after video is written before uploading
RETRY_INTERVAL_SECONDS = 15    # seconds before retrying a failed video upload

#Video and audio
BUFFER_LEN = 20
HANDLE_EVERY_FRAME = 4
HANDLE_EVERY_FRAME_OUT = 5
VIDEO_SEGMENT_LEN = 10
MAX_VIDEO_AGE_HOURS = 24

MAX_EVENT_AGE_HOURS = 24

RESOLUTIONS = {
    'P240':  (426, 240),
    'P480':  (854, 480),
    'P720':  (1280, 720),
    'P1080': (1920, 1080),
    'K2':    (1920, 1080),
    'K4':    (1920, 1080),
}

FPS=20
MAIN_SETTING = {
    'screenshot_format': 'P1080',
    'video_format': 'P720',
    'stream_format': 'P720',
}

WIDTH, HEIGHT = RESOLUTIONS.get(MAIN_SETTING['video_format'], (1280, 720))
FULL_HD_WIDTH = 1920
FULL_HD_HEIGHT = 1080
AUDIO_SR = 44100
CHANNELS = 1
AUDIO_DURATION = VIDEO_SEGMENT_LEN

OVERLAY = True

os.makedirs(LOCAL_PATH, exist_ok=True)
os.makedirs(MODEL_PATH, exist_ok=True)


violation_sounds = {
    'drinking': f'{SOUND_PATH}drinking.mp3',
    'eating': f'{SOUND_PATH}eating.mp3',
    'eyes_closed': f'{SOUND_PATH}eyes_closed.mp3',
    'mobile_usage': f'{SOUND_PATH}mobile_usage.mp3',
    'no_seatbelt': f'{SOUND_PATH}no_seatbelt.mp3',
    'smoking': f'{SOUND_PATH}smoking.mp3',
    'yawn': f'{SOUND_PATH}yawn.mp3',
    'inattentive_driving': f'{SOUND_PATH}inattentive_driving.mp3',
    'camera_obstructed': f'{SOUND_PATH}camera_obstructed.mp3',
    'car': f'{SOUND_PATH}car.mp3',
    'do_not_enter': f'{SOUND_PATH}do_not_enter.mp3',
    'do_not_stop': f'{SOUND_PATH}do_not_stop.mp3',
    'do_not_turn_l': f'{SOUND_PATH}do_not_turn_left.mp3',
    'do_not_turn_r': f'{SOUND_PATH}do_not_turn_right.mp3',
    'do_not_u_turn': f'{SOUND_PATH}do_not_u_turn.mp3',
    'enter_left_lane': f'{SOUND_PATH}enter_left_lane.mp3',
    'green_light': f'{SOUND_PATH}green_light.mp3',
    'left_right_lane': f'{SOUND_PATH}left_right_lane.mp3',
    'no_parking': f'{SOUND_PATH}no_parking.mp3',
    'ped_crossing': f'{SOUND_PATH}ped_crossing.mp3',
    'ped_zebra_cross': f'{SOUND_PATH}ped_zebra_cross.mp3',
    'railway_crossing': f'{SOUND_PATH}railway_crossing.mp3',
    'red_light': f'{SOUND_PATH}red_light.mp3',
    'roundabout': f'{SOUND_PATH}roundabout.mp3',
    'speed_limit_10': f'{SOUND_PATH}speed_limit_10.mp3',
    'speed_limit_100': f'{SOUND_PATH}speed_limit_100.mp3',
    'speed_limit_110': f'{SOUND_PATH}speed_limit_110.mp3',
    'speed_limit_120': f'{SOUND_PATH}speed_limit_120.mp3',
    'speed_limit_130': f'{SOUND_PATH}speed_limit_130.mp3',
    'speed_limit_15': f'{SOUND_PATH}speed_limit_15.mp3',
    'speed_limit_20': f'{SOUND_PATH}speed_limit_20.mp3',
    'speed_limit_30': f'{SOUND_PATH}speed_limit_30.mp3',
    'speed_limit_40': f'{SOUND_PATH}speed_limit_40.mp3',
    'speed_limit_5': f'{SOUND_PATH}speed_limit_5.mp3',
    'speed_limit_50': f'{SOUND_PATH}speed_limit_50.mp3',
    'speed_limit_60': f'{SOUND_PATH}speed_limit_60.mp3',
    'speed_limit_70': f'{SOUND_PATH}speed_limit_70.mp3',
    'speed_limit_80': f'{SOUND_PATH}speed_limit_80.mp3',
    'speed_limit_90': f'{SOUND_PATH}speed_limit_90.mp3',
    'speed_limit_25': f'{SOUND_PATH}speed_limit_25.mp3',
    'speed_limit_35': f'{SOUND_PATH}speed_limit_35.mp3',
    'speed_limit_45': f'{SOUND_PATH}speed_limit_45.mp3',
    'speed_limit_55': f'{SOUND_PATH}speed_limit_55.mp3',
    'speed_limit_65': f'{SOUND_PATH}speed_limit_65.mp3',
    'speed_limit_75': f'{SOUND_PATH}speed_limit_75.mp3',
    'speed_limit_85': f'{SOUND_PATH}speed_limit_85.mp3',
    'stop': f'{SOUND_PATH}stop.mp3',
    'traffic_light': f'{SOUND_PATH}traffic_light.mp3',
    'truck': f'{SOUND_PATH}truck.mp3',
    'u_turn': f'{SOUND_PATH}u_turn.mp3',
    'warning': f'{SOUND_PATH}warning.mp3',
    'yellow_light': f'{SOUND_PATH}yellow_light.mp3',
    'lane_departure': f'{SOUND_PATH}lane_departure.mp3',
    'bicycle': f'{SOUND_PATH}bicycle.mp3',
    'bus': f'{SOUND_PATH}bus.mp3',
    'motorbike': f'{SOUND_PATH}motorbike.mp3',
    'person': f'{SOUND_PATH}person.mp3',
    'no_vehicles': f'{SOUND_PATH}no_vehicles.mp3',
    'main_road': f'{SOUND_PATH}main_road.mp3',
    'yield': f'{SOUND_PATH}yield_sign.mp3',
    'left_lane': f'{SOUND_PATH}left_lane.mp3',
    'follow_distance': f'{SOUND_PATH}follow_distance.mp3',
    'shoulder_stop': f'{SOUND_PATH}shoulder_stop.mp3',
    'rolling_stop': f'{SOUND_PATH}rolling_stop.mp3',
    'passenger_detection': f'{SOUND_PATH}passenger_detection.mp3',
}

EVENT_CHOICE = {
    'drinking':'DRINKING', 
    'eyes_closed':'DROWSY', 
    'mobile_usage':'MOBILE_USAGE', 
    'no_seatbelt':'NO_SEAT_BELT',
    'smoking':'SMOKING', 
    'yawn':'DROWSY', 
    'inattentive_driving':'INATTENTIVE_DRIVING',
    'lane_departure':'LANE_DEPARTURE', 
    'left_lane':'LEFT_LANE', 
    'follow_distance':'FOLLOWING_DISTANCE', 
    'shoulder_stop':'SHOULDER_STOP', 
    'rolling_stop':'ROLLING_STOP',
    'camera_obstructed':'CAMERA_OBSTRUCTED',
    'passenger_detection':'PASSENGER_DETECTION',
}

VIOLATION_CLASSES_INNER = {
    'drinking', 'eyes_closed', 'mobile_usage', 'no_seatbelt',
    'smoking', 'yawn', 'inattentive_driving', 'camera_obstructed', 'passenger_detection'
}

OBSTRUCTION_CLASSES = {
    'eyes_closed', 'yawn', 'inattentive_driving', 'awake'
}

VIOLATION_CLASSES_FRONT = {
    'lane_departure', 'left_lane', 'follow_distance', 'shoulder_stop', 'rolling_stop', 'camera_obstructed'
}

known_distance = {'truck': 7, 'car': 7}  # meters
known_width = {'truck': 2.45, 'car': 1.8}  # meters

COOLDOWN_THRESHOLD = 60
CAMERA_OBSTRUCTION_THRESHOLD = 30

VIOLATION_RULES_INNER = {
    'no_seatbelt': {
        'min_speed': 10,
        'min_repeats': 3,
        'time_window': 900,
        'repeat_cooldown': 300,
        'cooldown': 900
    },
    'mobile_usage': {
        'min_speed': 10,
        'min_repeats': 3,
        'time_window': 900,
        'repeat_cooldown': 300,
        'cooldown': 900
    },
    'inattentive_driving': {
        'min_speed': 10,
        'duration_time': 5,
        'cooldown': 30
    },
    'camera_obstructed': {
        'min_speed': 10,
        'duration_time': 30,
        'cooldown': 900
    },
    'eyes_closed': {
        'min_speed': 10,
        'duration_time': 3,
        'cooldown': 15
    },
    'yawn': {
        'min_speed': 10,
        'duration_time': 3,
        'cooldown': 15
    },
    'smoking': {
        'min_speed': 10,
        'min_repeats': 3,
        'time_window': 60,
        'repeat_cooldown': 10,
        'cooldown': 60     
    },
    'drinking': {
        'min_speed': 10,
        'min_repeats': 3,
        'time_window': 3600,
        'repeat_cooldown': 1200,
        'cooldown': 1800     
    },
    'passenger_detection':{
        'min_speed': 10,
        'min_repeats': 3,
        'time_window': 900,
        'repeat_cooldown': 300,
        'cooldown': 900     
    }
}

VIOLATION_RULES_FRONT = {
    'lane_departure': {
        'min_speed': 10,
        'cooldown': 60
    },
    'left_lane': {
        'min_speed': 10,
        'duration_time': 5,
        'cooldown': 300
    },
    'camera_obstructed': {
        'min_speed': 0,
        'duration_time': 30,
        'cooldown': 900
    },
    'shoulder_stop': {
        'speed': 5,
        'duration_time':30,
        'cooldown': 60
    },
    'follow_distance': {
        'min_speed': 10,
        'time':0.5,
        'duration_time': 5,
        'cooldown': 30
    },
    'rolling_stop': {
        'min_speed': 10,
        'speed_check_times': 10,
        'check_interval': 1,
        'cooldown': 60
    },
}

SPEEDING_SETTING = {
    "light_over_limit": 1,
    "light_duration": 60,
    "moderate_over_limit": 5,
    "moderate_duration": 60,
    "heavy_over_limit": 9,
    "heavy_duration": 20,
    "severe_over_limit": 11,
    "severe_duration": 20,
    }


HARSH_EVENT_COEFFICIENTS = {
    'harsh_break': 0.4,
    'harsh_turn': 0.4,
    'harsh_acceleration': 0.4,
    'crash': 2.0
}



SPEED_LIMIT_CLASSES = {
    'speed_limit_5','speed_limit_10','speed_limit_15','speed_limit_20','speed_limit_25',
    'speed_limit_30','speed_limit_35','speed_limit_40','speed_limit_45','speed_limit_50',
    'speed_limit_55','speed_limit_60','speed_limit_65','speed_limit_70','speed_limit_75',
    'speed_limit_80','speed_limit_85','speed_limit_90','speed_limit_100','speed_limit_110',
    'speed_limit_120','speed_limit_130'
}

DEFAULT_CLASS_THRESHOLD = 0.4

OUTSIDE_CLASS_CONF_THRESHOLD = {
    'bicycle':DEFAULT_CLASS_THRESHOLD, 
    'bus':DEFAULT_CLASS_THRESHOLD, 
    'car':DEFAULT_CLASS_THRESHOLD, 
    'do_not_enter':DEFAULT_CLASS_THRESHOLD, 
    'do_not_turn_l':DEFAULT_CLASS_THRESHOLD, 
    'do_not_turn_r':DEFAULT_CLASS_THRESHOLD, 
    'do_not_u_turn': DEFAULT_CLASS_THRESHOLD, 
    'enter_left_lane': DEFAULT_CLASS_THRESHOLD, 
    'enter_right_lane': DEFAULT_CLASS_THRESHOLD, 
    'green_light': DEFAULT_CLASS_THRESHOLD, 
    'left_right_lane': DEFAULT_CLASS_THRESHOLD, 
    'main_road': DEFAULT_CLASS_THRESHOLD, 
    'motorbike': DEFAULT_CLASS_THRESHOLD, 
    'no_parking': DEFAULT_CLASS_THRESHOLD, 
    'no_vehicles': DEFAULT_CLASS_THRESHOLD, 
    'ped_crossing': DEFAULT_CLASS_THRESHOLD, 
    'person': DEFAULT_CLASS_THRESHOLD, 
    'railway_crossing': DEFAULT_CLASS_THRESHOLD, 
    'red_light': DEFAULT_CLASS_THRESHOLD, 
    'roundabout': DEFAULT_CLASS_THRESHOLD, 
    'speed_limit_10': DEFAULT_CLASS_THRESHOLD, 
    'speed_limit_15': DEFAULT_CLASS_THRESHOLD, 
    'speed_limit_20': DEFAULT_CLASS_THRESHOLD, 
    'speed_limit_25': DEFAULT_CLASS_THRESHOLD, 
    'speed_limit_30': DEFAULT_CLASS_THRESHOLD,
    'speed_limit_35': DEFAULT_CLASS_THRESHOLD, 
    'speed_limit_40': DEFAULT_CLASS_THRESHOLD, 
    'speed_limit_45': DEFAULT_CLASS_THRESHOLD, 
    'speed_limit_5': DEFAULT_CLASS_THRESHOLD, 
    'speed_limit_50': DEFAULT_CLASS_THRESHOLD, 
    'speed_limit_55': DEFAULT_CLASS_THRESHOLD, 
    'speed_limit_60': DEFAULT_CLASS_THRESHOLD, 
    'speed_limit_65': DEFAULT_CLASS_THRESHOLD, 
    'speed_limit_70': DEFAULT_CLASS_THRESHOLD, 
    'speed_limit_75': DEFAULT_CLASS_THRESHOLD, 
    'speed_limit_80': DEFAULT_CLASS_THRESHOLD, 
    'speed_limit_85': DEFAULT_CLASS_THRESHOLD, 
    'stop': DEFAULT_CLASS_THRESHOLD, 
    'train': DEFAULT_CLASS_THRESHOLD, 
    'truck': DEFAULT_CLASS_THRESHOLD, 
    'yellow_light': DEFAULT_CLASS_THRESHOLD, 
    'yield': DEFAULT_CLASS_THRESHOLD
    }

INSIDE_CLASS_CONF_THRESHOLD = {
    'awake': DEFAULT_CLASS_THRESHOLD, 
    'drinking': DEFAULT_CLASS_THRESHOLD, 
    'eating': DEFAULT_CLASS_THRESHOLD, 
    'eyes_closed': 0.7, 
    'inattentive_driving': DEFAULT_CLASS_THRESHOLD, 
    'mobile_usage': 0.3, 
    'no_seatbelt': DEFAULT_CLASS_THRESHOLD, 
    'seatbelt': DEFAULT_CLASS_THRESHOLD, 
    'smoking': 0.6, 
    'yawn': DEFAULT_CLASS_THRESHOLD
    }
