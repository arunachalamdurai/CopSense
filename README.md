# CopSense — Police Intelligence & Management System

CopSense is a comprehensive, AI-powered Management Information System (MIS) tailored for police districts (configured currently for Bihar Police, Patna District). It replaces legacy paper-based workflows with dynamic role-based dashboards, AI-driven crowd planning, active duty deployment tracking via GPS, custody safety monitoring, and a real-time crime hotspot heatmap.

## Features

- **Role-Based Access Control**: Secure JWT-based logins for District Head (SSP), Station Officers, Field Officers, and Citizens.
- **FIR & Complaints Management**: Full lifecycle tracking of cases with form validation and status updates.
- **AI Smart Alerts**: Background intelligent task scanner flags overdue investigations, idle patrols, or missed custody health updates.
- **Emergency Dispatch Optimizer**: Computes shortest distances (Harversine) and calculates logic-based unit ranking for dispatching available units responding to ongoing incidents.
- **Crime Heatmaps**: Visualizes current incident hotzones based on moving 30-day case data trends.

---

## 🛠 Prerequisites

Before you begin, ensure you have the following installed on your machine:
- **Node.js** (to run the simple frontend web server)
- **Python 3.9+** (to run the backend FastAPI server)

---

## 🚀 How to Run the Project locally

You need to run **two separate servers**: one for the backend API and one for the frontend UI.

### 1. Start the Backend API (FastAPI)

1. Open your terminal and navigate to the project directory:
   ```bash
   cd CopSense
   ```

2. Create and activate a Python virtual environment:
   ```bash
   # Windows
   python -m venv .venv
   .venv\Scripts\activate
   
   # Mac/Linux
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install all necessary dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   *(If you don't have a `requirements.txt`, install the defaults: `pip install fastapi uvicorn sqlalchemy passlib pydantic pyjwt python-multipart`)*

4. Run the Uvicorn server:
   ```bash
   uvicorn backend.main:app --port 8000 --reload
   ```
   *The backend will automatically create the required database (`copsense.db`) and seed the initial users. The Swagger API Docs are available at [http://localhost:8000/docs](http://localhost:8000/docs).*

### 2. Start the Frontend Application

The CopSense frontend is built using standard HTML, CSS, and Vanilla JavaScript. You just need to serve it using a local HTTP server.

1. Open a **new, separate terminal** tab and navigate to the root directory:
   ```bash
   cd CopSense
   ```

2. Start the web server using `npx`:
   ```bash
   npx http-server . -p 5500
   ```

3. Open your browser and navigate to:
   ```
   http://localhost:5500
   ```

---

## 🔐 Test Login Credentials

Once the portal is open in your browser, you can log in with one of the following pre-configured demo accounts to view different role-based permissions:

| Role | Username | Password | Notes |
| :--- | :--- | :--- | :--- |
| **District Head (SSP)** | `ssp.patna` | `Admin@123` | Full panoramic visibility over all stations |
| **Station Officer** | `so.patna` | `Officer@123` | Limited to their specific station jurisdiction |
| **Field Officer** | `fo.deepak` | `Field@123` | Mobile duty responses and tracking views |
| **Citizen** | `citizen.ravi` | `Citizen@123` | Restricted strictly to the Citizen Feedback portal |

*Enjoy your fully integrated, real-time CopSense simulation!*
