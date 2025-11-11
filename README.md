 SkillBridge
SkillBridge is a web-based AI-powered internship recommendation platform connecting students and companies. It offers dashboards for students, companies, and admins, with features like smart resume builder, real-time application tracking, and personalized internship suggestions.

It includes:
✅ Folder structure
✅ Team member roles (who did what)
✅ Setup & run instructions (starting with `main.py`)
✅ Clear feature list and tech stack

---

 📘 README.md for SkillBridge**

```markdown
 🌉 SkillBridge – AI-Powered Internship Recommendation Platform

SkillBridge is a web-based platform that bridges the gap between **students** and **companies** by providing AI-driven internship recommendations, resume building, and role-based dashboards.  
It simplifies the internship search, application, and management process.

---

🧩 Project Overview

 🎯 Objective
To develop a centralized web application that connects students and companies, provides AI-based internship recommendations, and streamlines the recruitment process.

💡 Key Features
- 🔐 Role-Based Access — Separate dashboards for Students, Companies, and Admin.
- 🧠 AI-Powered Recommendations — Suggests internships based on student skills.
- 📝 Smart Resume Builder — Auto-generates professional resumes.
- 📨 Real-Time Application Tracking — Students can track application status.
- 🏢 Company Dashboard — Post, approve, or reject internships easily.
- ⚙️ Admin Panel — Manage users, internships, and system logs.
- 🎨 Modern Web UI — Built with responsive front-end templates.

---

 🏗️ Folder Structure

```

Skillbridge/
│
├── main.py                     # Entry point for running the project
├── migrate_database.py         # Handles database migration/creation
├── models.py                   # Database models and ORM definitions
├── requirements.txt            # Dependencies file
│
├── templates/                  # HTML templates
│   ├── homepage.html
│   ├── student_dashboard.html
│   └── company_dashboard.html
│
├── static/                     # Static files (images, icons, CSS, JS)
│   └── favicon.png
│
├── instance/
│   └── users.db                # SQLite database (auto-generated)
│
└── .vscode/                    # Editor configuration (optional)

````

---

👥 Team Members and Work Division

| Name | Work Done |
|------|------------|
| Om Adavadkar | Frontend and UI|
| Ankik Bhattacharjee | Frontend templates, CSS, |
| Krishna Bhavsar| Project setup, deployment, integration, documentation , core backend  |
| Om Bhirud | Model design, data management, testing, and validation |

---

#⚙️ Tech Stack

| Layer | Technology |
|--------|-------------|
| Frontend | HTML, CSS, JavaScript |
| Backend | Python (Flask / Django Hybrid Structure) |
| Database | SQLite |
| AI/ML | Skill-based recommendation logic |
| Tools | Git, VS Code, Python 3.10+ |

---

 🧰 Prerequisites

Before running the project, ensure you have:
- Python 3.10+ installed  
- pip (Python package manager)

---

 🪜 Installation & Setup Guide

 Step 1 — Clone the Repository
```bash
git clone https://github.com/krishnab11/SkillBridge.git
cd SkillBridge
````

### Step 2 — Create a Virtual Environment

```bash
python -m venv env
```

Activate it:

* **Windows:**

  ```bash
  env\Scripts\activate
  ```
* **Linux/Mac:**

  ```bash
  source env/bin/activate
  ```

### Step 3 — Install Required Packages

```bash
pip install -r requirements.txt
```

### Step 4 — Run Database Migration

```bash
python migrate_database.py
```

### Step 5 — Start the Application

```bash
python main.py
```

Your app will start locally at:
👉 **[http://127.0.0.1:5000](http://127.0.0.1:5000)** (Flask default)
or
👉 **[http://127.0.0.1:8000](http://127.0.0.1:8000)** (if Django-based)

---

## 🖼️ Sample Screens (Suggested to Add)

| Homepage                   | Student Dashboard                      | Company Dashboard                      |
| -------------------------- | -------------------------------------- | -------------------------------------- |
| ![Home](docs/homepage.png) | ![Student](docs/student_dashboard.png) | ![Company](docs/company_dashboard.png) |

*(Add screenshots to the `docs/` folder)*

---

## 🔮 Future Scope

* 🤖 AI-based resume scoring
* 💬 Chatbot for internship queries
* 🔗 LinkedIn / Job API integration
* 📱 Mobile App version

---

## 🙏 Acknowledgment

We sincerely thank our mentors and institute for their guidance and support during the project.

---

## 🧾 License

This project is licensed under the **MIT License** — free for academic and educational use.

---

### ⭐ Don’t forget to star the repo if you like it!

```

---

Would you like me to:
1. Format this README with **badges (Python, Flask, License, Build)** for a professional GitHub look?  
2. Or generate a **`docs/` folder** with placeholders for screenshots and PPTs (so your repo looks clean and review-ready)?
```
