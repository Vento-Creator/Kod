# 🎬 Movie Finder Telegram Bot

Production-ready Telegram bot for managing and searching video content using aiogram 3.x and aiosqlite.

## Features

### 🎯 Core Functionality
- **Video Upload**: Admins can upload videos with unique numeric codes
- **Video Search**: Users can search videos by entering their code
- **Admin Panel**: Complete CRUD operations for video management
- **User Management**: Block/unblock users, view activity logs
- **Broadcast System**: Send messages to all users
- **Rate Limiting**: Advanced anti-spam protection with escalating bans

### 🔒 Security Features
- Rate limiting (10 requests per 60 seconds)
- Escalating ban system:
  - 1st violation: Warning
  - 2nd violation: 30-minute ban
  - 3rd violation: 1-hour ban
  - 4th violation: 2-hour ban
  - 5th violation: Permanent ban
- Automatic ban expiration for temporary bans
- Admin-only access to management features

### 📊 Database Schema
- **users**: User management and ban tracking
- **movies**: Video storage with unique codes
- **logs**: Search activity tracking

## Installation

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your BOT_TOKEN and ADMIN_IDS
```

4. Run the bot:
```bash
python main.py
```

## Project Structure

```
movie_finder_bot/
├── main.py              # Bot entry point
├── config.py            # Configuration management
├── requirements.txt     # Python dependencies
├── .env.example        # Environment variables template
├── database/           # Database layer
│   ├── __init__.py
│   ├── connection.py   # Database connection
│   ├── models.py       # Database models and initialization
│   └── repositories.py # Data access layer
├── handlers/           # Bot handlers
│   ├── __init__.py
│   ├── admin.py        # Admin panel handlers
│   └── user.py         # User interface handlers
├── keyboards/          # Inline keyboards
│   ├── __init__.py
│   ├── admin.py        # Admin keyboards
│   └── user.py         # User keyboards
└── middlewares/        # Custom middlewares
    ├── __init__.py
    └── rate_limit.py   # Rate limiting middleware
```

## Usage

### For Users
1. Start the bot with `/start`
2. Click "Video qidirish" (Search video)
3. Enter the video code
4. Receive the video

### For Admins
1. Access admin panel via `/admin` command (if implemented)
2. Upload videos with unique codes
3. Manage existing videos (edit/delete)
4. Manage users (block/unblock/view activity)
5. Send broadcast messages

## Development

### Adding New Features
1. Add new handlers in `handlers/` directory
2. Add new keyboards in `keyboards/` directory
3. Update database schema in `database/models.py` if needed
4. Add repository methods in `database/repositories.py`

### Testing
The bot includes comprehensive error handling and logging for debugging.

## License

MIT License
