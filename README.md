**Personal Diary Web App**

A secure, offline-first personal diary web application built using Flask.
Designed for local use only, this app lets you keep daily notes, attach images and view them in a calendar interface.
All data is stored locally using SQLite, so nothing is uploaded to the cloud.

Features:

Local Login System: Password-protected access with session management.

Calendar View: Select any date to view or write diary entries.

Image Attachments: Add .jpg or .png files to your diary entries (if you want to).

Automatic Date & Time: Entries are stored with timestamps.

Clean & Minimal UI: Easy-to-use interface with future scope for dark mode & theme customization.

Offline Use: No hosting or internet required, perfect for personal journaling.

Tech Stack:

Backend: Flask (Python)

Frontend: HTML, CSS, JavaScript (FullCalendar.js for calendar UI)

Database: SQLite (local storage)

File Handling: Pillow (for image uploads)

File Structure:

personal-diary/

│

├── app.py                 # Main Flask application

├── templates/             # HTML templates

├── static/                # CSS, JS, images

├── diary.db               # SQLite database (auto-created)

└── README.md              # Project documentation

Notes:

This app is intended for local use only.

Keep your login credentials safe, they are not recoverable if lost.

All data is stored in the local SQLite database, no cloud backup.

ScreenShots

Login Page:
<img width="1600" height="900" alt="image" src="https://github.com/user-attachments/assets/36ec2a71-1027-410a-8c15-21db7dbfcf40" />

Dashboard Page:
<img width="1600" height="900" alt="image" src="https://github.com/user-attachments/assets/8025667d-3feb-4ff4-b8bd-09ce12822d8a" />

Diary Page:
<img width="1600" height="900" alt="image" src="https://github.com/user-attachments/assets/6c3291ea-e2a3-438f-a76d-4fec1f82a874" />


License

This project is licensed under the MIT License, see the LICENSE file for details.

Connect Me:
LinkedIn: www.linkedin.com/in/om-prakash-anagani-1b17a9241
E_Mail: anaganiomprakashvarma@gmail.com

