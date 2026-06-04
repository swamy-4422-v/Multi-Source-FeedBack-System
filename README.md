# 📊 Multi-Source Feedback Intelligence System

A full-stack feedback analytics platform that collects customer feedback from multiple sources, processes it through an NLP pipeline, performs sentiment analysis, detects trends, and provides actionable insights through an interactive dashboard.

---

## 🚀 Live Demo

### Frontend Dashboard

https://multi-source-feedback-system.vercel.app

### Backend API

https://multi-source-feedback-system-backend.onrender.com

### API Documentation

https://multi-source-feedback-system-backend.onrender.com/docs

---

# 📌 Overview

Organizations receive customer feedback from multiple channels. Manually analyzing large volumes of feedback is time-consuming and inefficient.

The Multi-Source Feedback Intelligence System automates this workflow by:

* Collecting feedback from multiple sources
* Cleaning and normalizing text
* Performing sentiment analysis
* Categorizing issues automatically
* Detecting emerging trends
* Generating summary reports
* Displaying analytics through a modern React dashboard

---

# ✨ Key Features

## 1. Multi-Source Feedback Ingestion

Supports feedback collection through:

* Web Dashboard Submission
* REST API Integration
* Batch JSON Uploads

### Endpoints

```http
POST /feedback
POST /ingest/api
POST /ingest/batch
```

---

## 2. NLP Text Processing

Incoming feedback is automatically cleaned and normalized.

Processing includes:

* Lowercase normalization
* Whitespace cleanup
* Removal of unwanted symbols
* Consistent text formatting

---

## 3. Sentiment Analysis

Each feedback entry is classified as:

* Positive
* Neutral
* Negative

Additional confidence scores are generated for analysis and reporting.

---

## 4. Automatic Categorization

Feedback is grouped into categories such as:

| Category        | Examples                      |
| --------------- | ----------------------------- |
| Bug Report      | Application crashes, errors   |
| Feature Request | New functionality suggestions |
| Performance     | Slow loading, lagging         |
| Billing         | Payment issues                |
| Support         | Customer service concerns     |

---

## 5. Trend Detection

The system continuously monitors incoming feedback and identifies:

* Sudden issue spikes
* Frequently reported problems
* Emerging customer concerns

Trend alerts are automatically generated and stored.

---

## 6. Analytics Dashboard

Interactive React dashboard provides:

* Feedback volume statistics
* Sentiment distribution charts
* Category breakdowns
* Trend monitoring
* Recent feedback activity

---

## 7. AI Summary Reports

Automatically generates:

* Executive summaries
* Sentiment overviews
* Category insights
* Trend highlights

---

# 🏗️ System Architecture

```text
React Dashboard (Frontend)
          │
          ▼
     FastAPI Backend
          │
          ▼
 NLP Processing Pipeline
          │
 ┌────────┼────────┐
 ▼        ▼        ▼
Sentiment Category Trends
Analysis  Engine   Engine
          │
          ▼
      PostgreSQL
```

---

# 🛠️ Technology Stack

## Frontend

* React.js
* Axios
* Recharts
* CSS

## Backend

* FastAPI
* Python
* SQLAlchemy
* Pydantic

## Database

* PostgreSQL

## Deployment

* Vercel (Frontend)
* Render (Backend)
* Render PostgreSQL

---

# 📂 Project Structure

```text
multi-source-feedback-system/

├── frontend/
│   ├── src/
│   │   ├── App.js
│   │   └── components/
│
├── src/
│   ├── api/
│   │   ├── endpoints.py
│   │   └── middleware.py
│   │
│   ├── processing/
│   │   ├── cleaner.py
│   │   ├── analyzer.py
│   │   └── categorizer.py
│   │
│   ├── intelligence/
│   │   └── trend_detector.py
│   │
│   ├── actions/
│   │   └── reports.py
│   │
│   ├── database.py
│   └── tasks.py
│
├── requirements.txt
├── README.md
└── .gitignore
```

---

# ⚙️ Local Setup

## Clone Repository

```bash
git clone <repository-url>
cd multi-source-feedback-system
```

---

## Backend Setup

Create a `.env` file:

```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/feedback_db
OPENAI_API_KEY=your_api_key
RATE_LIMIT=100
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run backend:

```bash
uvicorn src.api.endpoints:app --reload
```

Backend URL:

```text
http://localhost:8000
```

---

## Frontend Setup

```bash
cd frontend
npm install
npm start
```

Frontend URL:

```text
http://localhost:3000
```

---

# 📊 Example Workflow

1. User submits feedback
2. Feedback enters ingestion pipeline
3. Text is cleaned and normalized
4. Sentiment is analyzed
5. Category is assigned
6. Trend detector evaluates patterns
7. Results are stored in PostgreSQL
8. Dashboard updates analytics

---

# 🎯 Evaluation Criteria Mapping

| Requirement            | Implementation              |
| ---------------------- | --------------------------- |
| Multi-Source Ingestion | FastAPI ingestion endpoints |
| NLP Processing         | Text cleaning pipeline      |
| Sentiment Analysis     | Analyzer module             |
| Categorization         | Categorizer engine          |
| Trend Detection        | Trend detector              |
| Prioritization         | Alert generation logic      |
| Dashboard              | React analytics UI          |
| Reporting              | Automated summary reports   |

---

# 📈 Future Enhancements

* Real-time WebSocket updates
* Advanced ML-based classification
* User authentication and roles
* Export reports to PDF
* Email and Slack alerts
* Trend forecasting models

---

# 👨‍💻 Author

Vechalapu Swamy Hyma Kumar

Built using React, FastAPI, PostgreSQL, and NLP techniques for automated feedback intelligence and analytics.
