# import time
# from datetime import datetime
# import os

# # Specify the target time (7:00 AM)
# target_time = "07:00"

# # Function to wait until the specified time
# def wait_until(target_time):
#     while True:
#         now = datetime.now().strftime("%H:%M")
#         if now == target_time:
#             break
#         print(f"Current time is {now}, waiting until {target_time}...")
#         time.sleep(60)  # Check the time every minute

# # Wait until 7 AM
# wait_until(target_time)

# # Once it's 7 AM, run the script
# os.system("python main.py -y 2024 -w 39")
