# 🔧 Backend

This folder will contain the backend API server for the fridge spoilage detection system.

## 🎯 Planned Features

- **REST API**: FastAPI endpoints for all ML models
- **Image Processing**: Handle file uploads and preprocessing
- **Model Integration**: Connect to computer vision models
- **Database**: Store results and user data
- **Authentication**: User management and security

## 🛠️ Technology Stack (Planned)

- **Framework**: FastAPI
- **Database**: PostgreSQL or SQLite
- **Authentication**: JWT tokens
- **File Storage**: Local or cloud storage
- **API Documentation**: Auto-generated with FastAPI

## 📁 Structure (To Be Created)

```
backend/
├── app/
│   ├── api/            # API endpoints
│   ├── models/         # Database models
│   ├── services/       # Business logic
│   └── utils/          # Helper functions
├── tests/              # API tests
├── requirements.txt    # Dependencies
└── main.py            # FastAPI app
```

## 🚀 Getting Started (When Ready)

```bash
# Install dependencies
pip install -r requirements.txt

# Start development server
uvicorn main:app --reload

# Access API docs
open http://localhost:8000/docs
```

## 🔗 Integration with Computer Vision

The backend will integrate with the models in `../computer_vision/`:
- Load trained models from `../computer_vision/models/`
- Use inference scripts from `../computer_vision/scripts/`
- Process images and return results

---

**This folder is ready for backend development!** ⚙️