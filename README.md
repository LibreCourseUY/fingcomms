# Fingcomms - Group Directory for Fing Students

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/Fingdev/fingcomms)

Welcome to Fingcomms! This project is a simple directory that allows Fing (Facultad de Ingeniería, UdelaR) students to find and connect with study groups and projects.

## What is this project?

Fingcomms allows you to:
- View a list of engineering student groups
- Search groups by name or category
- Add new groups to the directory

It's designed to help incoming students find study partners and collaborative projects.

## Tech Stack

- **Backend** (server-side): FastAPI + SQLite
- **Frontend** (visual interface): Vue.js
- **Containers**: Docker

## Quick Start

### Option 1: With Docker (Recommended for Beginners)

Docker is a tool that lets you run applications in "containers" without manually installing dependencies.

1. Make sure Docker is installed on your computer
   - [Download Docker Desktop](https://www.docker.com/products/docker-desktop)

2. Open a terminal in the project folder

3. Run:
   ```bash
   docker-compose up --build
   ```

4. Open your browser and visit: `http://localhost:8000`

Done! The application is now running.

### Option 2: Without Docker (For Python users)

1. Make sure you have Python installed (version 3.9 or higher)

2. Create a virtual environment (an isolated workspace):
   ```bash
   python -m venv venv
   ```

3. Activate the virtual environment:
   - On Linux/Mac: `source venv/bin/activate`
   - On Windows: `venv\Scripts\activate`

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Run the server:
   ```bash
   uvicorn main:app --reload
   ```

6. Open your browser at: `http://localhost:8000`

## How to Contribute

Want to help improve Fingcomms? Excellent!

Check out our contribution guide in [CONTRIBUTING.md](CONTRIBUTING.md) for step-by-step instructions.

## Found a Problem?

If you found a bug or have an idea for improvement:
1. Check if someone already reported it in the Issues section
2. If not, create a new Issue using the available templates

## License

This project is under MIT license. See [LICENSE](LICENSE) for details.

---

New to development? Don't worry, we all started somewhere. If you have questions, feel free to ask in Issues or seek help from the Fing community.
