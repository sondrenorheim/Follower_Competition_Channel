"""
Quick video file checker using OpenCV
"""
import cv2
import os

video_path = "Videos/Day_35/fighter_arena_day_35.mp4"

print(f"Checking video: {video_path}")
print(f"File exists: {os.path.exists(video_path)}")
print(f"File size: {os.path.getsize(video_path) / (1024*1024):.2f} MB")

try:
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        print("❌ ERROR: Cannot open video file")
    else:
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        codec = int(cap.get(cv2.CAP_PROP_FOURCC))
        codec_str = "".join([chr((codec >> 8 * i) & 0xFF) for i in range(4)])

        duration = frame_count / fps if fps > 0 else 0

        print("\n✅ Video file is readable!")
        print(f"Resolution: {width}x{height}")
        print(f"FPS: {fps}")
        print(f"Frame count: {frame_count}")
        print(f"Duration: {duration:.2f} seconds ({duration/60:.2f} minutes)")
        print(f"Codec: {codec_str}")

        # Try reading first frame
        ret, frame = cap.read()
        if ret:
            print(f"✅ First frame read successfully (shape: {frame.shape})")
        else:
            print("❌ Cannot read first frame")

        cap.release()

except Exception as e:
    print(f"❌ ERROR: {e}")
