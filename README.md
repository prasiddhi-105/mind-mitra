# MindMitra Backend

An AI-powered mental wellness backend that detects emotional distress using voice tone, facial expression, and text analysis, and responds with mood journaling, CBT-based AI chatbot, and SOS alerts.

## 🚀 Features

- **Multi-modal Emotion Detection**: Text sentiment, voice tone, and facial expression analysis
- **CBT-based AI Chatbot**: Guided therapeutic conversations
- **SOS Alert System**: Emergency notifications via SMS/Email
- **Mood Journaling**: Track emotional patterns over time
- **Real-time Analytics**: Emotional trend analysis and reporting
- **Secure Authentication**: JWT-based user management
- **Role-based Access**: User, Admin, and Therapist roles

## 🏗️ Architecture

```
Mobile App (React Native)
       |
       | REST API / WebSocket
       |
Backend (FastAPI)
       |             |              |
 Emotion Detection   Chatbot     SOS & Alerts
       |             |              |
 Pre-trained Models  NLP Engine   Twilio / Email
```

## 🛠️ Tech Stack

- **Framework**: FastAPI
- **Database**: MongoDB with Motor (async)
- **Authentication**: JWT with Firebase Auth
- **File Storage**: Firebase Storage
- **AI/ML**: Transformers, DeepFace, VADER
- **Background Tasks**: Celery with Redis
- **Messaging**: Twilio SMS, SMTP Email
- **Real-time**: WebSocket support

## 📦 Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd mind-mitra
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run the application**
   ```bash
   uvicorn app.main:app --reload
   ```

## 🔧 Configuration

Create a `.env` file with the following variables:

```env
# Database
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=mindmitra

# Authentication
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Firebase
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_PRIVATE_KEY_ID=your-private-key-id
FIREBASE_PRIVATE_KEY=your-private-key
FIREBASE_CLIENT_EMAIL=your-client-email
FIREBASE_CLIENT_ID=your-client-id

# Twilio
TWILIO_ACCOUNT_SID=your-account-sid
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_PHONE_NUMBER=your-twilio-number

# Email
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# AI Models
HUGGINGFACE_API_KEY=your-huggingface-key
```

## 📡 API Endpoints

### Authentication
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login
- `POST /api/auth/refresh` - Refresh token
- `GET /api/auth/profile` - Get user profile

### Emotion Analysis
- `POST /api/analyze/text` - Text sentiment analysis
- `POST /api/analyze/audio` - Voice tone emotion detection
- `POST /api/analyze/image` - Facial expression emotion detection

### Chatbot
- `POST /api/chatbot` - CBT-guided chatbot response
- `GET /api/chatbot/history` - Chat history

### Journal
- `GET /api/journal` - Get mood entries
- `POST /api/journal` - Create mood entry
- `PUT /api/journal/{entry_id}` - Update mood entry
- `DELETE /api/journal/{entry_id}` - Delete mood entry

### SOS System
- `POST /api/sos/send` - Trigger SOS alert
- `POST /api/sos/cancel` - Cancel SOS alert
- `GET /api/sos/history` - SOS alert history

### User Management
- `GET /api/user/profile` - Get user profile
- `PUT /api/user/profile` - Update user profile
- `GET /api/user/contacts` - Get emergency contacts
- `POST /api/user/contacts` - Add emergency contact

### Analytics
- `GET /api/stats/mood-trends` - Emotional trend data
- `GET /api/stats/engagement` - User engagement metrics
- `GET /api/stats/alerts` - Alert statistics

## 🧠 AI Model Integration

### Text Sentiment Analysis
- **Model**: VADER + BERT (transformers)
- **Input**: Text string
- **Output**: `{label: "negative", score: 0.87}`

### Voice Tone Analysis
- **Model**: DeepSpectrum + librosa
- **Input**: Audio file (.wav)
- **Output**: `{label: "anxious", confidence: 0.76}`

### Facial Emotion Detection
- **Model**: DeepFace
- **Input**: Image file
- **Output**: `{label: "sad", confidence: 0.82}`

## 🚨 SOS Alert System

### Trigger Criteria
- Text + Face + Voice all show "critical state"
- Multiple "depressed" flags in <24 hours
- Manual trigger by user

### Alert Methods
- **SMS**: Via Twilio
- **Email**: Via SMTP server
- **Push Notification**: Via Firebase Cloud Messaging

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_auth.py
```

## 📊 Data Models

### User
```python
{
    "id": "user_id",
    "email": "user@example.com",
    "name": "John Doe",
    "role": "user",  # user, admin, therapist
    "emergency_contacts": [...],
    "created_at": "2023-01-01T00:00:00Z"
}
```

### Journal Entry
```python
{
    "id": "entry_id",
    "user_id": "user_id",
    "content": "Today I felt...",
    "mood_score": 0.75,
    "emotion_labels": ["happy", "content"],
    "created_at": "2023-01-01T00:00:00Z"
}
```

### SOS Alert
```python
{
    "id": "alert_id",
    "user_id": "user_id",
    "trigger_type": "automatic",  # automatic, manual
    "severity": "high",
    "status": "sent",  # sent, cancelled, acknowledged
    "created_at": "2023-01-01T00:00:00Z"
}
```

## 🔐 Security Features

- **JWT Authentication**: Secure token-based auth
- **Data Encryption**: AES-256 for sensitive data
- **Rate Limiting**: API rate limiting
- **Input Validation**: Pydantic models
- **CORS**: Cross-origin resource sharing
- **Role-based Access**: User permission management

## 🚀 Deployment

### Docker
```bash
# Build image
docker build -t mindmitra-backend .

# Run container
docker run -p 8000:8000 mindmitra-backend
```

### Production
```bash
# Install production dependencies
pip install -r requirements.txt

# Run with gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

## 📈 Monitoring & Analytics

- **Health Checks**: `/health` endpoint
- **Metrics**: Prometheus metrics
- **Logging**: Structured logging with correlation IDs
- **Error Tracking**: Sentry integration
- **Performance**: APM monitoring

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For support, email support@mindmitra.com or create an issue in the repository. 

## 🐳 Local Development Setup

To run the application locally using Docker, follow these steps:

1. **Clone the repository:**
```bash
   git clone [https://github.com/1809gaurav/mind-mitra.git](https://github.com/1809gaurav/mind-mitra.git)
   cd mind-mitra

docker compose up --build
