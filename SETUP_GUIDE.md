# 🎬 Movie Finder Bot - Setup Guide

## 📋 Prerequisites
- Python 3.10+
- Telegram Bot Token (from @BotFather)
- Your Telegram User ID (for admin access)

## 🚀 Installation Steps

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables
```bash
cp .env.example .env
```

Edit `.env` file:
```
BOT_TOKEN=your_actual_bot_token_here
ADMIN_IDS=your_telegram_id_1,your_telegram_id_2
```

### 3. Run the Bot
```bash
python main.py
```

## 🎯 Usage Guide

### For Regular Users

1. **Start the bot**
   - Send `/start` to the bot
   - You'll see the main menu

2. **Search for videos**
   - Click "🎬 Video qidirish"
   - Enter the video code (numeric)
   - Receive the video

3. **Get help**
   - Click "ℹ️ Yordam" for instructions

### For Admins

1. **Access Admin Panel**
   - Send `/admin` to the bot
   - Only works if your ID is in ADMIN_IDS

2. **Upload Videos**
   - Click "🎬 Video yuklash"
   - Send a video file
   - Enter a unique numeric code
   - Bot will check for duplicate codes

3. **Manage Videos**
   - Click "📋 Video boshqarish"
   - Browse through videos with pagination
   - Edit captions or codes
   - Delete videos

4. **Manage Users**
   - Click "👥 Foydalanuvchilar"
   - View all users
   - Block/unblock users
   - View user activity logs

5. **Broadcast Messages**
   - Click "📢 Xabar yuborish"
   - Send a message to all users
   - See delivery statistics

## 🔒 Security Features

### Rate Limiting
- 10 requests per 60 seconds per user
- Escalating ban system:
  - Warning 1: ⚠️ Warning message
  - Warning 2: ⏰ 30-minute ban
  - Warning 3: ⏰ 1-hour ban
  - Warning 4: ⏰ 2-hour ban
  - Warning 5: ⛔️ Permanent ban

### Admin Protection
- All admin features require ADMIN_IDS authentication
- User management and blocking capabilities
- Activity monitoring

## 📊 Database Structure

### Users Table
- `id`: Auto-increment ID
- `telegram_id`: Unique Telegram user ID
- `username`: Telegram username
- `full_name`: User's full name
- `is_blocked`: Block status
- `warning_count`: Number of warnings
- `ban_until`: Temporary ban expiration
- `created_at`: Account creation timestamp

### Movies Table
- `id`: Auto-increment ID
- `code`: Unique numeric code
- `file_id`: Telegram file ID
- `caption`: Video description
- `created_at`: Upload timestamp

### Logs Table
- `id`: Auto-increment ID
- `user_id`: User's Telegram ID
- `searched_code`: Code searched for
- `timestamp`: Search timestamp

## 🛠️ Troubleshooting

### Bot doesn't start
- Check BOT_TOKEN is correct
- Verify internet connection
- Check Python version (3.10+)

### Database errors
- Delete `bot_database.db` and restart
- Check file permissions

### Rate limiting issues
- Wait for temporary ban to expire
- Contact admin to unblock

### Video upload fails
- Check video file size (Telegram limits)
- Verify code is unique
- Check bot has permission to send videos

## 📝 Development Notes

### Adding New Features
1. Add handlers in `handlers/` directory
2. Add keyboards in `keyboards/` directory
3. Update database schema if needed
4. Add repository methods for database operations

### Code Structure
- `main.py`: Bot entry point
- `config.py`: Configuration management
- `database/`: Data access layer
- `handlers/`: Bot event handlers
- `keyboards/`: UI keyboards
- `middlewares/`: Custom middleware
- `services/`: Business logic (extensible)

## 🔧 Configuration

Edit `config.py` to customize:
- Rate limiting parameters
- Ban durations
- Warning thresholds
- Database path

## 📞 Support

For issues or questions:
1. Check logs for error messages
2. Verify configuration in `.env`
3. Test with a fresh database
4. Check Telegram Bot API status
