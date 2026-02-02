# PartSelect Chatbot Frontend

Modern Next.js 14 frontend with TypeScript for the PartSelect Chatbot.

## Features

✅ **Modern Chat Interface**
- Real-time messaging with loading states
- Message history with timestamps
- User/Assistant avatars
- Validation score display

✅ **Product Cards**
- Beautiful card design for parts
- Price, brand, availability badges
- Direct links to PartSelect product pages
- Installation video links when available

✅ **PartSelect Branding**
- Blue color scheme (#0066CC)
- Clean, professional design
- Mobile-responsive layout

✅ **Session Management**
- Automatic session creation
- Conversation history
- Reset chat functionality

✅ **User Experience**
- Quick suggestion chips
- Enter to send, Shift+Enter for newline
- Auto-scroll to latest message
- Loading indicators
- Error handling

## Installation

```bash
cd frontend
npm install
```

## Development

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

## Build for Production

```bash
npm run build
npm start
```

## Environment Variables

Create a `.env.local` file:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Stack

- **Next.js 14** - React framework with App Router
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling
- **Lucide React** - Icons
- **Axios** - API client

## Components

- `ChatInterface` - Main chat UI
- `MessageBubble` - Individual message display
- `PartCard` - Product card with details and links

## API Integration

Connects to FastAPI backend at `http://localhost:8000`:
- `/health` - Health check
- `/api/session/new` - Create session
- `/api/chat` - Send messages
- `/api/session/{id}/history` - Get history
