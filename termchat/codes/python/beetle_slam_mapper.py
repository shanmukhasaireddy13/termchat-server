#!/usr/bin/env python3
"""
BeetleBot Experiment 3: LiDAR SLAM, Frontier Autonomous Exploration & Mapping
ROS 2 Jazzy node for autonomous SLAM mapping with RPLidar S1, floor camera segmentation,
visual ArUco landmarks, and map serialization.
"""

import os, sys, time, json, math, subprocess, signal, warnings
from collections import deque
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from rclpy.signals import SignalHandlerOptions
from nav_msgs.msg import OccupancyGrid
from sensor_msgs.msg import LaserScan, Image
from geometry_msgs.msg import Twist
from std_srvs.srv import Trigger
from tf2_ros import Buffer, TransformListener


# ------------------------------ SETTINGS ------------------------------------
BRINGUP_CMD = ("source /opt/ros/jazzy/setup.bash && "
              "source /home/veerobot/lyra_ws/install/setup.bash && "
              "ros2 launch lyra_bringup robot.launch.py mode:=slam camera:=true imu:=true")
ENV = ("source /opt/ros/jazzy/setup.bash && "
      "source /home/veerobot/lyra_ws/install/setup.bash && ")
MAP_DIR = os.path.expanduser("~/maps")
MAP_NAME = "pab_map"
MAP_FRAME, BASE_FRAME = "map", "base_link"
ODOM_FRAME = "odom"
CALIBRATE = True         # start-up check: creeps ~0.2 m and turns ~40 deg to verify lidar/odometry/motor directions
SWEEP_AT_START = False   # not needed with a 360 deg lidar (RPLidar S1); True = spin one turn first
ABORT_ON_BAD_HEADING = False   # True = stop the run if it keeps moving opposite to its heading
CAMERA_TOPIC = "/camera/image_raw"
CMD_TOPIC = "/cmd_vel_nav"


# ---- ROBOT SIZE: measure from the lidar centre to the farthest edge of the robot body ----
ROBOT_RADIUS = 0.15      # m
LIN_SPEED = 0.12         # m/s  (slow = safer in tight spaces)
MIN_LIN_SPEED = 0.06     # m/s  never command less than this while moving (motor dead-band).
                        #      If the robot still does not move, raise it (e.g. 0.08).
ANG_SPEED = 0.35         # rad/s  (slow turns = better odometry and cleaner SLAM map)
# The RPLidar S1 cannot see anything closer than ~0.2 m, so keep the stop distance above that.
STOP_DIST = 0.30         # m  emergency stop distance in front (measured from the lidar)
AVOID_DIST = ROBOT_RADIUS + 0.25   # m  obstacles closer than this push the robot away (all around)
MIN_VALID_RANGE = 0.10   # m  ignore lidar hits closer than this (robot's own body/mount)
REAR_STOP = 0.28         # m  minimum free space behind (from lidar) before any reversing
ALLOW_REVERSE = True     # robot may back up in recovery (only when the 360 scan shows free space behind)
# Lidar yaw relative to base_link (rad). None = read automatically from TF.
# If the lidar is mounted facing backwards but TF says 0, set math.pi here.
LIDAR_YAW_OFFSET = None
# If after fixing the lidar yaw the robot STILL physically drives backwards when told
# to go forward, set this to -1.0 (motor/driver sign is inverted).
LIN_SIGN = 1.0


# ---- camera obstacle layer (monocular floor segmentation, fused with the lidar) ----
# The camera must face FORWARD. Distances come from ground-plane geometry, so measure
# CAM_HEIGHT / CAM_TILT_DOWN / CAM_HFOV for good accuracy. Works best on a plain floor.
USE_CAMERA_AVOID = True
CAM_HEIGHT = 0.15        # m   camera height above the floor
CAM_TILT_DOWN = 0.0      # rad camera pitched down by this angle (0 = looking level)
CAM_HFOV = 1.09          # rad horizontal field of view (62.5 deg = Pi Camera v2; webcams ~1.0-1.2)
CAM_X_OFFSET = 0.0       # m   camera position forward of the lidar (negative = behind it)
CAM_YAW = 0.0            # rad camera yaw relative to the robot front
CAM_FLOOR_ROWS = (0.80, 0.95)  # image rows (fraction of height) that are surely bare floor.
                              # Move them up if the robot's own body shows at the image bottom.
CAM_TOL_K, CAM_MIN_TOL, CAM_MAX_SD = 3.0, 14.0, 28.0   # floor colour tolerance settings
CAM_BINS, CAM_RUN_ROWS = 11, 3     # image columns checked / rows an obstacle must span
CAM_MIN_RANGE, CAM_MAX_RANGE = 0.30, 1.20   # m  ranges the camera is trusted in
CAM_OBS_TTL = 15.0       # s  camera obstacles stay in the planner this long
INFLATE_M = ROBOT_RADIUS + 0.06       # m  normal obstacle inflation
INFLATE_RELAX = ROBOT_RADIUS + 0.02   # m  relaxed inflation for tight gaps
INFLATE_MIN = ROBOT_RADIUS - 0.02     # m  last resort (live lidar/camera safety still protects)
LOOKAHEAD = 0.25         # m
ARRIVE_M = 0.30          # m  goal counts as reached
BLACKLIST_R = 0.30       # m
MIN_CLUSTER_M = 0.10     # m  ignore frontier clusters shorter than this
GAIN = 0.5               # prefers larger frontiers over slightly closer ones
GOAL_TIMEOUT = 60.0      # s
PLAN_PERIOD = 2.0        # s
DONE_AFTER = 6           # consecutive failed plans (after retries) -> finished
MIN_RUNTIME = 30.0       # s never finish before this
MAX_RUNTIME = 30 * 60    # s hard limit
AUTOSAVE_S = 60.0
# ----------------------------------------------------------------------------




def sh(cmd, timeout=None):
   return subprocess.run(["bash", "-c", ENV + cmd], timeout=timeout,
                         capture_output=True, text=True)




def dilate(m, k):
   out = m.copy()
   for s in range(1, k + 1):
       out[:, s:] |= m[:, :-s]
       out[:, :-s] |= m[:, s:]
   out2 = out.copy()
   for s in range(1, k + 1):
       out2[s:, :] |= out[:-s, :]
       out2[:-s, :] |= out[s:, :]
   return out2




class Mapper(Node):
   def __init__(self):
       super().__init__("auto_mapper")
       self.exec = None
       self.cmd = self.create_publisher(Twist, CMD_TOPIC, 10)
       self.create_subscription(OccupancyGrid, "/map", self.on_map, 1)
       self.create_subscription(LaserScan, "/scan", self.on_scan, 5)
       self.create_subscription(Image, CAMERA_TOPIC, self.on_image, 1)
       self.tfbuf = Buffer()
       self.tfl = TransformListener(self.tfbuf, self)
       self.arm_cli = self.create_client(Trigger, "/lyra/arm")
       self.disarm_cli = self.create_client(Trigger, "/lyra/disarm")


       self.map = None
       self.scan = None
       self.pts = None            # (angles, ranges, increment) in the ROBOT frame, full 360
       self.calibrating = False
       self.heading_bad = 0
       self.abort_reason = None
       self.skip_save = False
       self.lidar_yaw = None
       self.path = []
       self.goal = None
       self.goal_t = 0.0
       self.blacklist = []
       self.bl_clears = 0
       self.no_frontier = 0
       self.replan_now = True
       self.last_plan = 0.0
       self.finished = False
       self.start_t = time.time()
       self.rec_until, self.rec_v, self.rec_w = 0.0, 0.0, 0.0
       self.stuck_ref = None
       self.last_v = 0.0
       self.landmarks = {}
       self.last_img_t = 0.0
       self.last_log = 0.0
       self.autosave_proc = None
       self.aruco = None
       self.cv2 = None
       self.cam_pts = None                  # (angles, ranges, time) virtual lidar points from the camera
       self.cam_obs = []                    # [(map_x, map_y, time)] camera obstacles for the planner
       self.cam_hist = deque(maxlen=3)
       self.last_cam_t = 0.0
       self.cam_log_t = 0.0
       self.cam_err_t = 0.0
       self.enc_warned = False
       self.follow_time = 0.0
       self.tf_wait_t = None
       self.no_path_since = None
       self.blocked_since = None
       self.state = "starting"
       self.last_status = 0.0
       self.dbg_front = self.dbg_near = float("inf")
       self.last_cmd = (0.0, 0.0)
       try:
           import cv2
           self.cv2 = cv2
       except Exception as e:
           self.get_logger().warn(f"OpenCV not available - camera features disabled ({e})")
       if self.cv2 is not None:
           try:
               d = self.cv2.aruco.getPredefinedDictionary(self.cv2.aruco.DICT_4X4_50)
               self.aruco = self.cv2.aruco.ArucoDetector(d, self.cv2.aruco.DetectorParameters())
           except Exception as e:
               self.get_logger().warn(f"ArUco disabled ({e})")


       self.create_timer(0.1, self.control, callback_group=MutuallyExclusiveCallbackGroup())
       self.create_timer(0.5, self.plan_tick, callback_group=MutuallyExclusiveCallbackGroup())
       self.create_timer(AUTOSAVE_S, self.autosave, callback_group=MutuallyExclusiveCallbackGroup())


   # ---------------- callbacks ----------------
   def on_map(self, m):
       self.map = m


   def on_scan(self, s):
       self.scan = s
       if self.lidar_yaw is None:
           if LIDAR_YAW_OFFSET is not None:
               self.lidar_yaw = float(LIDAR_YAW_OFFSET)
               self.get_logger().info(f"Lidar yaw offset (manual): {self.lidar_yaw:.2f} rad")
           else:
               try:
                   t = self.tfbuf.lookup_transform(BASE_FRAME, s.header.frame_id, rclpy.time.Time())
                   q = t.transform.rotation
                   self.lidar_yaw = math.atan2(2 * (q.w * q.z + q.x * q.y),
                                               1 - 2 * (q.y * q.y + q.z * q.z))
                   self.get_logger().info(
                       f"Lidar yaw offset (from TF {s.header.frame_id}->{BASE_FRAME}): {self.lidar_yaw:.2f} rad")
               except Exception:
                   if self.tf_wait_t is None:
                       self.tf_wait_t = time.time()
                   if time.time() - self.tf_wait_t < 5.0:
                       return                               # give TF a few seconds to appear
                   self.lidar_yaw = 0.0
                   self.get_logger().warn(
                       f"No TF {s.header.frame_id}->{BASE_FRAME} after 5 s - assuming the lidar faces "
                       "forward (yaw 0). Check your robot TF tree if avoidance looks wrong.")
       r = np.asarray(s.ranges, dtype=np.float32)
       a = s.angle_min + np.arange(len(r)) * s.angle_increment + self.lidar_yaw
       a = (a + math.pi) % (2 * math.pi) - math.pi          # beam angle in robot frame
       ok = np.isfinite(r) & (r > max(s.range_min, MIN_VALID_RANGE)) & (r < s.range_max)
       a_l, r_l = a[ok], r[ok]
       cp = self.cam_pts                                    # add fresh camera obstacles as virtual beams
       if cp is not None and time.time() - cp[2] < 0.8 and len(cp[0]):
           a_l = np.concatenate([a_l, cp[0]])
           r_l = np.concatenate([r_l, cp[1]])
       self.pts = (a_l, r_l, abs(float(s.angle_increment)))   # one atomic assignment


   def on_image(self, msg):
       if self.cv2 is None:
           return
       now = time.time()
       do_aruco = self.aruco is not None and now - self.last_img_t >= 0.5
       do_cam = USE_CAMERA_AVOID and now - self.last_cam_t >= 0.2
       if not (do_aruco or do_cam):
           return
       try:
           ch = {"rgb8": 3, "bgr8": 3, "mono8": 1}.get(msg.encoding)
           if ch is None:
               if not self.enc_warned:
                   self.get_logger().warn(f"Camera encoding '{msg.encoding}' not supported "
                                          "(need rgb8 / bgr8 / mono8) - camera features off")
                   self.enc_warned = True
               return
           img = np.frombuffer(msg.data, np.uint8).reshape(msg.height, msg.step)[:, :msg.width * ch]
           if ch == 3:
               img = np.ascontiguousarray(img.reshape(msg.height, msg.width, 3))
           if do_cam:
               self.last_cam_t = now
               self.camera_obstacles(img, msg.encoding)
           if do_aruco:
               self.last_img_t = now
               if ch == 3:
                   gray = self.cv2.cvtColor(img, self.cv2.COLOR_RGB2GRAY if msg.encoding == "rgb8"
                                            else self.cv2.COLOR_BGR2GRAY)
               else:
                   gray = img
               _, ids, _ = self.aruco.detectMarkers(gray)
               pose = self.pose()
               if ids is not None and pose:
                   for i in ids.flatten():
                       if int(i) not in self.landmarks:
                           self.landmarks[int(i)] = {"robot_x": pose[0], "robot_y": pose[1]}
                           self.get_logger().info(f"Landmark ID {int(i)} near ({pose[0]:.2f}, {pose[1]:.2f})")
       except Exception as e:
           if now - self.cam_err_t > 10:
               self.cam_err_t = now
               self.get_logger().warn(f"Camera processing error: {e}")


   def camera_obstacles(self, img, enc):
       """Floor segmentation: anything not floor-coloured, seen above the floor patch, is an obstacle.
       Result: virtual lidar beams (self.cam_pts) + temporary planner obstacles (self.cam_obs)."""
       cv2 = self.cv2
       H0, W0 = img.shape[:2]
       W = 160
       H = max(16, int(H0 * W / W0))
       sm = cv2.resize(img, (W, H), interpolation=cv2.INTER_AREA)
       if sm.ndim == 3:
           sm = cv2.cvtColor(sm, cv2.COLOR_RGB2LAB if enc == "rgb8" else cv2.COLOR_BGR2LAB)
       feat = cv2.GaussianBlur(sm, (5, 5), 0).astype(np.float32)
       if feat.ndim == 2:
           feat = feat[:, :, None]


       r0, r1 = int(H * CAM_FLOOR_ROWS[0]), int(H * CAM_FLOOR_ROWS[1])
       c0, c1 = int(W * 0.30), int(W * 0.70)
       patch = feat[r0:r1, c0:c1].reshape(-1, feat.shape[2])
       mu, sd = patch.mean(0), patch.std(0)
       if float(sd.max()) > CAM_MAX_SD:          # reference patch is not plain floor: no trustworthy model
           return
       tol = np.maximum(CAM_TOL_K * sd, CAM_MIN_TOL)
       floor = (np.abs(feat - mu) <= tol).all(axis=2).astype(np.uint8)
       k3 = np.ones((3, 3), np.uint8)
       floor = cv2.morphologyEx(cv2.morphologyEx(floor, cv2.MORPH_OPEN, k3), cv2.MORPH_CLOSE, k3)
       nonfloor = floor == 0


       fx = (W / 2.0) / math.tan(CAM_HFOV / 2.0)
       cx, cy = W / 2.0, H / 2.0
       s_t, c_t = math.sin(CAM_TILT_DOWN), math.cos(CAM_TILT_DOWN)
       top = max(int(cy - fx * math.tan(CAM_TILT_DOWN)) + 3, 0)     # stay below the horizon
       nb = CAM_BINS
       edges = np.linspace(0, W, nb + 1).astype(int)
       centers = 0.5 * (edges[:-1] + edges[1:])
       bin_ang = -np.arctan((centers - cx) / fx) + CAM_YAW           # + = left of the robot front
       res_bins = np.full(nb, np.inf)
       for i in range(nb):
           col = nonfloor[:, edges[i]:edges[i + 1]].mean(axis=1) > 0.5
           run, hit = 0, None
           for v in range(r0 - 1, top - 1, -1):                      # walk up from the floor patch
               if col[v]:
                   run += 1
                   if run >= CAM_RUN_ROWS:
                       hit = v + run - 1                              # lowest row of the obstacle = floor contact
                       break
               else:
                   run = 0
           if hit is None:
               continue
           x_c, y_c = (centers[i] - cx) / fx, (hit - cy) / fx
           yy, zz = y_c * c_t + s_t, c_t - y_c * s_t
           if yy <= 1e-3:
               continue
           sc = CAM_HEIGHT / yy
           fwd, left = sc * zz + CAM_X_OFFSET, -sc * x_c
           rng = math.hypot(fwd, left)
           if fwd > 0 and CAM_MIN_RANGE <= rng <= CAM_MAX_RANGE:
               res_bins[i] = rng


       self.cam_hist.append(res_bins)
       hist = np.stack(list(self.cam_hist))
       det = np.isfinite(hist)
       conf = det.sum(axis=0) >= min(2, len(hist))                   # seen in >=2 of the last 3 frames
       far = np.where(det, hist, -np.inf).max(axis=0)                # least severe range among detections


       angs, rngs = [], []
       half = 0.4 * CAM_HFOV / nb
       for i in np.where(conf)[0]:
           for da in (-half, 0.0, half):
               angs.append(bin_ang[i] + da)
               rngs.append(far[i])
       if angs:
           a = (np.array(angs) + math.pi) % (2 * math.pi) - math.pi
           self.cam_pts = (a.astype(np.float32), np.array(rngs, np.float32), time.time())
       else:
           self.cam_pts = None


       now = time.time()
       pose = self.pose()
       if pose and conf.any():                                       # remember them for the planner
           for i in np.where(conf & np.isfinite(res_bins))[0]:
               wx = pose[0] + res_bins[i] * math.cos(pose[2] + bin_ang[i])
               wy = pose[1] + res_bins[i] * math.sin(pose[2] + bin_ang[i])
               dup = next((j for j, o in enumerate(self.cam_obs) if math.hypot(wx - o[0], wy - o[1]) < 0.10), None)
               if dup is None:
                   self.cam_obs.append((wx, wy, now))
               else:
                   self.cam_obs[dup] = (self.cam_obs[dup][0], self.cam_obs[dup][1], now)
       self.cam_obs = [o for o in self.cam_obs if now - o[2] < CAM_OBS_TTL][-300:]
       if now - self.cam_log_t > 10:
           self.cam_log_t = now
           self.get_logger().info(f"Camera layer: {int(conf.sum())}/{nb} directions blocked, "
                                  f"{len(self.cam_obs)} planner obstacles")


   # ---------------- helpers ----------------
   def pose(self):
       return self.pose_in(MAP_FRAME)


   def pose_in(self, frame):
       try:
           t = self.tfbuf.lookup_transform(frame, BASE_FRAME, rclpy.time.Time())
           q = t.transform.rotation
           yaw = math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))
           return t.transform.translation.x, t.transform.translation.y, yaw
       except Exception:
           return None


   def drive(self, v, w):
       t = Twist()
       t.linear.x, t.angular.z = float(v) * LIN_SIGN, float(w)
       self.last_v = float(v)
       self.last_cmd = (float(v), float(w))
       self.cmd.publish(t)


   def stop(self):
       for _ in range(10):
           self.drive(0, 0)
           time.sleep(0.02)


   # ---- 360 degree scan helpers (angles are in the robot frame: 0 = front, +left) ----
   def sector_min(self, lo, hi):
       """Closest obstacle between angles lo..hi (rad). lo > hi means the sector wraps behind."""
       if self.pts is None:
           return float("inf")
       a, r, _ = self.pts
       m = ((a >= lo) & (a <= hi)) if lo <= hi else ((a >= lo) | (a <= hi))
       return float(r[m].min()) if m.any() else float("inf")


   def all_min(self):
       if self.pts is None or len(self.pts[1]) == 0:
           return float("inf")
       return float(self.pts[1].min())


   def rear_min(self):
       return self.sector_min(2.6, -2.6)


   def corridor_min(self):
       """Distance to the nearest obstacle inside the strip the robot body will sweep going forward."""
       if self.pts is None:
           return float("inf")
       a, r, _ = self.pts
       x, y = r * np.cos(a), r * np.sin(a)
       m = (x > 0) & (np.abs(y) < ROBOT_RADIUS + 0.04)
       return float(x[m].min()) if m.any() else float("inf")


   def can_spin(self, w):
       """True if turning in place (w>0 = left) will not swing the body into something."""
       c = ROBOT_RADIUS
       if w > 0:      # CCW: front-left and rear-right of the body sweep outwards
           return self.sector_min(0.3, 1.6) > c and self.sector_min(-2.84, -1.6) > c
       return self.sector_min(-1.6, -0.3) > c and self.sector_min(1.6, 2.84) > c


   def flee_angle(self):
       """Direction (robot frame) pointing away from all nearby obstacles, from the full 360 scan."""
       a, r, _ = self.pts
       m = r < AVOID_DIST
       if not m.any():
           return 0.0
       wgt = 1.0 / r[m] - 1.0 / AVOID_DIST
       return math.atan2(-(wgt * np.sin(a[m])).sum(), -(wgt * np.cos(a[m])).sum())


   def best_heading(self):
       """Most open direction in the whole 360 scan (robot frame): returns (angle, clearance_m)."""
       a, r, _ = self.pts
       edges = np.linspace(-math.pi, math.pi, 37)
       idx = np.clip(np.digitize(a, edges) - 1, 0, 35)
       clear = np.full(36, 6.0)
       np.minimum.at(clear, idx, r)
       sm = np.minimum(np.minimum(np.roll(clear, 1), clear), np.roll(clear, -1))   # needs a wide gap
       centers = 0.5 * (edges[:-1] + edges[1:])
       score = sm - 0.15 * np.abs(centers)                           # prefer small turns
       k = int(np.argmax(score))
       return float(centers[k]), float(sm[k])


   def safe_drive(self, v, w, last_resort=False):
       """Final safety filter for every command: no blind reversing, no spinning into obstacles."""
       if v < 0 and (not (ALLOW_REVERSE or last_resort) or self.rear_min() < REAR_STOP):
           v = 0.0
       if v > 0.0:
           v = max(v, MIN_LIN_SPEED)                        # stay above the motor dead-band
       if v == 0.0 and w != 0.0 and not self.can_spin(w):
           if self.can_spin(-w):
               w = -w
           else:
               w = 0.0
               if last_resort and self.rear_min() > REAR_STOP:
                   v = -0.06                       # boxed in on both sides: ease back
       self.drive(v, w)


   def blacklisted(self, x, y):
       return any(math.hypot(x - bx, y - by) < BLACKLIST_R for bx, by in self.blacklist)


   def ban_goal(self, why):
       if self.goal:
           self.blacklist.append(self.goal)
           self.get_logger().info(f"Goal done/banned ({why}); blacklist={len(self.blacklist)}")
       self.goal, self.path = None, []
       self.replan_now = True


   # ---------------- planning ----------------
   def find_goal(self, g, infl_m, p, use_cam=True):
       H, W = g.shape
       res = self.map.info.resolution
       ox, oy = self.map.info.origin.position.x, self.map.info.origin.position.y
       k = max(1, int(math.ceil(infl_m / res)))
       blocked = dilate(g >= 65, k)
       now_t = time.time()
       for wx, wy, t in (list(self.cam_obs) if use_cam else []):   # camera obstacles (temporary)
           if now_t - t > CAM_OBS_TTL:
               continue
           ccx, ccy = int((wx - ox) / res), int((wy - oy) / res)
           if 0 <= ccx < W and 0 <= ccy < H:
               blocked[max(0, ccy - 1):ccy + 2, max(0, ccx - 1):ccx + 2] = True
       free = (g == 0) & ~blocked
       rx, ry = int((p[0] - ox) / res), int((p[1] - oy) / res)
       if not (0 <= rx < W and 0 <= ry < H):
           return None
       y0, y1, x0, x1 = max(0, ry - k), ry + k + 1, max(0, rx - k), rx + k + 1
       free[y0:y1, x0:x1] |= (g[y0:y1, x0:x1] == 0)       # robot may leave its own inflated zone


       unk = g == -1
       nu = np.zeros_like(unk)
       nu[1:, :] |= unk[:-1, :]; nu[:-1, :] |= unk[1:, :]
       nu[:, 1:] |= unk[:, :-1]; nu[:, :-1] |= unk[:, 1:]
       fr = (free & nu).ravel().tolist()
       fl = free.ravel().tolist()


       N = H * W
       dist = [-1] * N
       parent = [-1] * N
       start = ry * W + rx
       dist[start] = 0
       parent[start] = start
       dq = deque([start])
       fcells = []
       while dq:
           c = dq.popleft()
           if fr[c]:
               fcells.append(c)
           cy, cx = divmod(c, W)
           d = dist[c] + 1
           for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
               ny, nx = cy + dy, cx + dx
               if 0 <= ny < H and 0 <= nx < W:
                   n = ny * W + nx
                   if fl[n] and dist[n] < 0:
                       dist[n] = d
                       parent[n] = c
                       dq.append(n)


       # cluster reachable frontier cells (8-connected)
       fset = set(fcells)
       best, best_cost = None, float("inf")
       while fset:
           s = fset.pop()
           comp, st = [s], [s]
           while st:
               c = st.pop()
               cy, cx = divmod(c, W)
               for dy in (-1, 0, 1):
                   for dx in (-1, 0, 1):
                       ny, nx = cy + dy, cx + dx
                       if 0 <= ny < H and 0 <= nx < W:
                           n = ny * W + nx
                           if n in fset:
                               fset.remove(n)
                               comp.append(n)
                               st.append(n)
           size = len(comp) * res
           if size < MIN_CLUSTER_M:
               continue
           rep = min(comp, key=lambda c: dist[c])
           wx, wy = ox + (rep % W + 0.5) * res, oy + (rep // W + 0.5) * res
           if self.blacklisted(wx, wy):
               continue
           cost = dist[rep] * res - GAIN * size
           if self.goal and math.hypot(wx - self.goal[0], wy - self.goal[1]) < 0.8:
               cost = -1e9                                   # hysteresis: keep current goal
           if cost < best_cost:
               best, best_cost = rep, cost
       if best is None:
           return None


       cells = []
       c = best
       while c != start:
           cells.append(c)
           c = parent[c]
       cells.reverse()
       return [(ox + (c % W + 0.5) * res, oy + (c // W + 0.5) * res) for c in cells]


   def plan_tick(self):
       if self.finished or self.map is None:
           return
       now = time.time()
       if not self.replan_now and now - self.last_plan < PLAN_PERIOD:
           return
       p = self.pose()
       if p is None:
           return
       self.replan_now = False
       self.last_plan = now
       m = self.map
       g = np.array(m.data, dtype=np.int8).reshape(m.info.height, m.info.width)


       if now - self.last_log > 10:
           known = int((g != -1).sum()) * m.info.resolution ** 2
           self.get_logger().info(f"Mapped area ~{known:.1f} m2, blacklist={len(self.blacklist)}")
           self.last_log = now


       if self.goal and now - self.goal_t > GOAL_TIMEOUT:
           self.ban_goal("timeout")


       path = None
       for infl in (INFLATE_M, INFLATE_RELAX, INFLATE_MIN):
           path = self.find_goal(g, infl, p)
           if path:
               break
       if not path and self.cam_obs:                       # camera layer may be over-cautious: retry without it
           path = self.find_goal(g, INFLATE_RELAX, p, use_cam=False)
           if path:
               self.get_logger().info("Path found only after ignoring camera obstacles")
       if not path and self.blacklist and self.bl_clears < 2:
           self.get_logger().info("Nothing left - clearing blacklist and retrying")
           self.blacklist, self.bl_clears = [], self.bl_clears + 1
           path = self.find_goal(g, INFLATE_MIN, p)


       if not path:
           self.no_frontier += 1
           self.path = []
           self.get_logger().info(f"No reachable frontier ({self.no_frontier}/{DONE_AFTER})")
           if self.no_frontier >= DONE_AFTER and now - self.start_t > MIN_RUNTIME:
               self.finished = True
           return
       self.no_frontier = 0
       new_goal = path[-1]
       if self.goal is None or math.hypot(new_goal[0] - self.goal[0], new_goal[1] - self.goal[1]) > 0.8:
           self.goal_t = now
           self.get_logger().info(f"New goal ({new_goal[0]:.2f}, {new_goal[1]:.2f}), {len(path)} cells")
       self.goal = new_goal
       self.path = path


   # ---------------- start-up drive-direction calibration ----------------
   def spin_for(self, sec):
       end = time.time() + sec
       while time.time() < end:
           self.exec.spin_once(timeout_sec=0.05)


   def grab(self, n=5):
       """Median of n raw scans (same beam indexing every time) and each beam's robot-frame angle."""
       rs = []
       for _ in range(n):
           self.spin_for(0.12)
           s = self.scan
           r = np.asarray(s.ranges, dtype=np.float32)
           rs.append(np.where(np.isfinite(r) & (r > 0.15) & (r < s.range_max), r, np.nan))
       L = min(len(x) for x in rs)
       with warnings.catch_warnings():
           warnings.simplefilter("ignore")
           med = np.nanmedian(np.stack([x[:L] for x in rs]), axis=0)
       s = self.scan
       return med, s.angle_min + np.arange(L) * s.angle_increment + self.lidar_yaw


   @staticmethod
   def lidar_motion(r0, r1, ang):
       """+1 if the lidar saw the robot move toward base_link +x, -1 if toward -x, None if unclear."""
       ok = np.isfinite(r0) & np.isfinite(r1)
       dr, a = (r1 - r0)[ok], ang[ok]
       m = np.abs(dr) < 0.5
       dr, a = dr[m], a[m]
       if len(dr) < 50:
           return None, 0.0
       score = -float((dr * np.cos(a)).sum()) / len(dr)      # >0: ranges ahead shrank / behind grew
       return (1 if score > 0.01 else -1 if score < -0.01 else None), score


   @staticmethod
   def lidar_rotation(r0, r1, inc):
       """Rotation (rad, + = CCW) the lidar saw between two scans, from the best circular beam shift."""
       maxk = int(math.radians(60) / inc)
       ks = np.arange(-maxk, maxk + 1)
       scores = np.full(len(ks), np.inf)
       for n, k in enumerate(ks):
           sh = np.roll(r0, -int(k))
           m = np.isfinite(sh) & np.isfinite(r1)
           if m.sum() >= 100:
               scores[n] = float(np.abs(r1[m] - sh[m]).mean())
       fin = np.isfinite(scores)
       if fin.sum() < 10:
           return None
       n = int(np.argmin(scores))
       if scores[n] > 0.7 * float(np.median(scores[fin])):       # no clear best shift
           return None
       return float(ks[n]) * inc


   def calibrate_direction(self):
       global LIN_SIGN
       log = self.get_logger()
       self.calibrating = True
       try:
           t0 = time.time()
           while self.pts is None and time.time() - t0 < 10:
               self.spin_for(0.1)
           if self.pts is None:
               log.warn("Calibration skipped: no lidar->base_link TF yet.")
               return True
           log.info("Calibration: looking for free space, then creeping ~0.2 m and turning ~40 deg ...")
           t0 = time.time()
           while time.time() - t0 < 20 and not (self.corridor_min() > 0.8 and self.rear_min() > 0.6):
               self.safe_drive(0.0, 0.4)
               self.spin_for(0.05)
           self.stop()
           if not (self.corridor_min() > 0.8 and self.rear_min() > 0.6):
               log.warn("Calibration skipped: not enough free space around the robot. "
                        "Move it to an open spot and restart.")
               return True


           # ---------- test 1: forward creep ----------
           r0, ang = self.grab()
           o0 = self.pose_in(ODOM_FRAME)
           t0 = time.time()
           while time.time() - t0 < 2.0:
               if min(self.corridor_min(), self.rear_min()) < 0.30:
                   break
               self.drive(0.12, 0.0)
               self.spin_for(0.05)
           self.stop()
           self.spin_for(0.8)
           r1, _ = self.grab()
           o1 = self.pose_in(ODOM_FRAME)
           lid, score = self.lidar_motion(r0, r1, ang)
           od, dxo = None, 0.0
           if o0 and o1:
               dxo = (o1[0] - o0[0]) * math.cos(o0[2]) + (o1[1] - o0[1]) * math.sin(o0[2])
               od = 1 if dxo > 0.03 else -1 if dxo < -0.03 else None
           name = {1: "FORWARD (+x)", -1: "BACKWARD (-x)", None: "unclear"}
           log.info(f"Calibration 1/2 (move): lidar saw {name[lid]} (score {score:+.3f}); "
                    f"odometry says {name[od]} ({dxo:+.2f} m); command was forward.")


           # ---------- test 2: turn in place ----------
           rot_msg = None
           if self.can_spin(0.4) or self.can_spin(-0.4):
               ra, ang2 = self.grab()
               q0 = self.pose_in(ODOM_FRAME)
               t0 = time.time()
               while time.time() - t0 < 1.8:
                   self.safe_drive(0.0, 0.4)
                   self.spin_for(0.05)
               self.stop()
               self.spin_for(0.8)
               rb, _ = self.grab()
               q1 = self.pose_in(ODOM_FRAME)
               if q0 and q1 and len(ang2) > 2:
                   rot_od = (q1[2] - q0[2] + math.pi) % (2 * math.pi) - math.pi
                   th = self.lidar_rotation(ra, rb, abs(float(ang2[1] - ang2[0])))
                   th_txt = "unclear" if th is None else f"{th:+.2f} rad"
                   log.info(f"Calibration 2/2 (turn): odometry says {rot_od:+.2f} rad, lidar saw {th_txt}.")
                   if th is not None and abs(rot_od) > 0.15 and abs(th) > 0.10 and rot_od * th < 0:
                       rot_msg = (
                           "TURN DIRECTION MISMATCH: odometry says the robot turned one way but the lidar scan "
                           f"rotated the other way ({rot_od:+.2f} vs {th:+.2f} rad). Either the lidar scan is "
                           "mirrored or odometry yaw is inverted.")
           else:
               log.warn("Calibration 2/2 skipped: no room to turn on the spot.")


           def flip():
               global LIN_SIGN
               LIN_SIGN = -LIN_SIGN
               log.warn(f"Drive direction was inverted -> command sign flipped automatically "
                        f"(LIN_SIGN={LIN_SIGN:+.0f}).")


           def verdict():
               if lid is None and od is None:
                   return True
               if lid is None:
                   if od < 0:
                       flip()
                   return True
               if od is None:
                   if lid < 0:
                       flip()
                   return True
               if lid > 0 and od > 0:
                   return True
               if lid < 0 and od < 0:
                   flip()
                   return True
               if lid < 0 and od > 0:
                   self.abort_reason = "LIDAR FRAME MISMATCH: odometry moved forward but lidar saw reverse."
               else:
                   self.abort_reason = "ODOMETRY SIGN MISMATCH: lidar saw forward but odometry reported reverse."
               return False


           ok = verdict()
           if ok and rot_msg:
               self.abort_reason = rot_msg
               ok = False
           elif ok:
               log.info("Calibration finished: no direction problems found.")
           if not ok:
               self.skip_save = True
           return ok
       finally:
           self.stop()
           self.calibrating = False


   def report_scan_coverage(self):
       s = self.scan
       if s is None or self.pts is None:
           return
       n = len(s.ranges)
       a = s.angle_min + np.arange(n) * s.angle_increment + self.lidar_yaw
       a = (a + math.pi) % (2 * math.pi) - math.pi
       fov = math.degrees(s.angle_max - s.angle_min)
       self.get_logger().info(f"Lidar: {n} beams, field of view {fov:.0f} deg")


   def initial_sweep(self):
       self.calibrating = True
       try:
           p = self.pose()
           if p is None:
               return
           self.get_logger().info("Start-up sweep: turning 360 deg to scan all around ...")
           last, total, t0 = p[2], 0.0, time.time()
           while total < 2 * math.pi - 0.25 and time.time() - t0 < 25:
               self.safe_drive(0.0, 0.5)
               self.spin_for(0.05)
               q = self.pose()
               if q:
                   total += abs((q[2] - last + math.pi) % (2 * math.pi) - math.pi)
                   last = q[2]
           self.stop()
           self.spin_for(1.0)
       finally:
           self.stop()
           self.calibrating = False


   def control(self):
       self._control()
       now = time.time()
       if now - self.last_status > 2.0 and not self.finished and not self.calibrating:
           self.last_status = now
           v, w = self.last_cmd
           self.get_logger().info(
               f"[status] {self.state} | front={self.dbg_front:.2f} near={self.dbg_near:.2f} "
               f"path={len(self.path)} cmd=({v:+.2f} m/s, {w:+.2f} rad/s)")


   def _control(self):
       if self.pts is None:
           self.state = "waiting for lidar data / TF"
       if self.finished or self.pts is None or self.calibrating:
           return
       p = self.pose()
       if p is None:
           return
       now = time.time()
       x, y, yaw = p


       left = self.sector_min(0.3, 2.4)
       right = self.sector_min(-2.4, -0.3)
       front = self.corridor_min()
       near = self.all_min()
       self.dbg_front, self.dbg_near = front, near


       if now < self.rec_until:
           self.state = "recovery manoeuvre"
           self.safe_drive(self.rec_v, self.rec_w)
           return


       if front < STOP_DIST:
           self.path = []
           self.replan_now = True
           self.state = f"BLOCKED ahead ({front:.2f} m) -> turning"
           if self.blocked_since is None:
               self.blocked_since = now
           if ALLOW_REVERSE and now - self.blocked_since > 3.0 and self.rear_min() > REAR_STOP:
               self.get_logger().info("Blocked ahead for 3 s - backing up")
               self.ban_goal("blocked")
               self.rec_until, self.rec_v, self.rec_w = now + 1.5, -0.08, 0.0
               self.blocked_since = None
               return
           ang, _ = self.best_heading()
           if abs(ang) < 0.2:
               ang = 1.0 if left > right else -1.0
           self.safe_drive(0.0, ANG_SPEED if ang > 0 else -ANG_SPEED, last_resort=True)
           return


       self.blocked_since = None
       if near < ROBOT_RADIUS + 0.02:
           self.state = f"obstacle very close ({near:.2f} m) -> moving away"
           ang, _ = self.best_heading()
           if abs(ang) < 0.5:
               self.safe_drive(0.08, max(-ANG_SPEED, min(ANG_SPEED, 1.5 * ang)))
           else:
               self.safe_drive(0.0, ANG_SPEED if ang > 0 else -ANG_SPEED)
           return


       if self.stuck_ref is None or now - self.stuck_ref[0] > 6.0:
           if self.stuck_ref and self.follow_time > 3.0:
               _, rx, ry, ryaw = self.stuck_ref
               dx, dy = x - rx, y - ry
               d = math.hypot(dx, dy)
               along = dx * math.cos(ryaw) + dy * math.sin(ryaw)
               dyaw = abs((yaw - ryaw + math.pi) % (2 * math.pi) - math.pi)
               if d < 0.08:
                   self.get_logger().warn("Stuck - recovering")
                   self.ban_goal("stuck")
                   turn = 0.5 if left > right else -0.5
                   if ALLOW_REVERSE and self.rear_min() > REAR_STOP:
                       self.rec_until, self.rec_v, self.rec_w = now + 1.8, -0.08, 0.3 * turn
                   else:
                       self.rec_until, self.rec_v, self.rec_w = now + 1.5, 0.0, turn
           self.stuck_ref = (now, x, y, yaw)
           self.follow_time = 0.0


       if not self.path:
           self.state = "no path yet (planner finding frontier)"
           self.safe_drive(0.0, 0.0)
           return


       while len(self.path) > 1 and math.hypot(self.path[0][0] - x, self.path[0][1] - y) < 0.12:
           self.path.pop(0)
       if self.goal and math.hypot(self.goal[0] - x, self.goal[1] - y) < ARRIVE_M:
           self.state = "goal reached"
           self.ban_goal("reached")
           self.drive(0.0, 0.0)
           return


       tgt = self.path[-1]
       for wp in self.path:
           if math.hypot(wp[0] - x, wp[1] - y) >= LOOKAHEAD:
               tgt = wp
               break
       err = math.atan2(tgt[1] - y, tgt[0] - x) - yaw
       err = (err + math.pi) % (2 * math.pi) - math.pi


       a, r, inc = self.pts
       m = (r < AVOID_DIST) & (np.abs(a) < 1.9)
       w_avoid = 0.0
       if m.any():
           wgt = 1.0 / r[m] - 1.0 / AVOID_DIST
           w_avoid = float(max(-0.6, min(0.6, -(wgt * np.sin(a[m])).sum() * inc)))


       if abs(err) > 1.4:
           self.state = "turning toward goal"
           self.safe_drive(0.0, ANG_SPEED if err > 0 else -ANG_SPEED)
       else:
           slow = max(0.3, min(1.0, (front - STOP_DIST) / 0.4 + 0.3))
           align = max(0.25, math.cos(err))
           w = max(-ANG_SPEED, min(ANG_SPEED, 1.5 * err + w_avoid))
           self.follow_time += 0.1
           self.state = "following path"
           self.safe_drive(LIN_SPEED * slow * align, w)


   def autosave(self):
       if self.finished or self.map is None:
           return
       if self.autosave_proc and self.autosave_proc.poll() is None:
           return
       os.makedirs(MAP_DIR, exist_ok=True)
       base = os.path.join(MAP_DIR, MAP_NAME + "_autosave")
       self.autosave_proc = subprocess.Popen(
           ["bash", "-c", ENV + f"ros2 run nav2_map_server map_saver_cli -f {base}"],
           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


   def call(self, cli, name):
       if not cli.wait_for_service(timeout_sec=5.0):
           return
       f = cli.call_async(Trigger.Request())
       end = time.time() + 5
       while not f.done() and time.time() < end:
           self.exec.spin_once(timeout_sec=0.1)


def save_everything(node):
   os.makedirs(MAP_DIR, exist_ok=True)
   base = os.path.join(MAP_DIR, MAP_NAME)
   print(f"[SAVE] Saving map to {base} ...")
   r = sh(f"ros2 run nav2_map_server map_saver_cli -f {base} --ros-args -p save_map_timeout:=10.0",
          timeout=40)
   sh(f"ros2 service call /slam_toolbox/serialize_map slam_toolbox/srv/SerializePoseGraph \"{{filename: '{base}'}}\"", timeout=20)
   if node.landmarks:
       with open(os.path.join(MAP_DIR, "landmarks.json"), "w") as f:
           json.dump(node.landmarks, f, indent=2)
       print(f"[SAVE] {len(node.landmarks)} landmarks -> landmarks.json")
   print("[SAVE] Map saved OK" if os.path.exists(base + ".yaml") else "[SAVE] Map file not found.")


def main():
   print("[1/5] Starting bringup (lidar, camera, imu, slam)...")
   bring = subprocess.Popen(["bash", "-c", "exec bash -c '" + BRINGUP_CMD + "'"], start_new_session=True)
   rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
   node = Mapper()
   ex = MultiThreadedExecutor(num_threads=4)
   ex.add_node(node)
   node.exec = ex
   try:
       print("[2/5] Waiting for /scan, /map and TF (up to 60 s)...")
       t0 = time.time()
       while time.time() - t0 < 60 and not (node.scan and node.map and node.pose()):
           ex.spin_once(timeout_sec=0.2)
       if not (node.scan and node.map and node.pose()):
           print("Not ready. If /map is missing, start slam: ros2 launch slam_toolbox online_async_launch.py")
           return


       print("[3/5] Arming robot...")
       node.call(node.arm_cli, "arm")
       node.report_scan_coverage()
       if CALIBRATE:
           print("[3b/5] Checking drive direction (robot will creep ~0.2 m)...")
           if not node.calibrate_direction():
               print("\n[ABORT] " + (node.abort_reason or "Calibration failed."))
               return


       if SWEEP_AT_START:
           node.initial_sweep()


       print("[4/5] Exploring the whole lab. Ctrl+C anytime - map is saved first.")
       node.start_t = time.time()
       while rclpy.ok() and not node.finished and time.time() - node.start_t < MAX_RUNTIME:
           ex.spin_once(timeout_sec=0.05)


   except KeyboardInterrupt:
       print("\n[CTRL+C] Stopping robot and saving map...")
   finally:
       signal.signal(signal.SIGINT, signal.SIG_IGN)
       node.finished = True
       try:
           node.stop()
           if not node.skip_save:
               save_everything(node)
           node.stop()
           node.call(node.disarm_cli, "disarm")
       except Exception as e:
           print("Shutdown error:", e)
       print("[5/5] Shutting down bringup...")
       try:
           os.killpg(os.getpgid(bring.pid), signal.SIGINT)
           bring.wait(timeout=10)
       except Exception:
           try:
               os.killpg(os.getpgid(bring.pid), signal.SIGKILL)
           except Exception:
               pass
       try:
           ex.shutdown()
           node.destroy_node()
           rclpy.try_shutdown()
       except Exception:
           pass
       print(f"Map: {MAP_DIR}/{MAP_NAME}.yaml")


if __name__ == "__main__":
   main()
