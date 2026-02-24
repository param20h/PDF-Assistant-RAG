import os
from dotenv import load_dotenv
load_dotenv()

from models import User

username = input("Enter the username to make admin: ")
user = User.find_by_username(username)

if user:
    user.is_admin = True
    user.save()
    print(f"Success! '{username}' is now an admin. You can access the Admin Dashboard at /admin via the profile links.")
else:
    print(f"User '{username}' not found. Please make sure you have registered/logged in first!")
