# SCIPHR Redesign - Frontend

Modern, FightSignal-inspired redesign of the SCIPHR UFC prediction platform.

## 🚀 Features

- **Hero Fight Card** - Stunning main event showcase with countdown timer
- **Value Bet Indicators** - Shows when model disagrees with Vegas (YOUR EDGE!)
- **Quick Links** - Fast navigation to key features
- **Responsive Design** - Works on desktop, tablet, and mobile
- **Modern UI** - Glassmorphism, gradients, and smooth animations

## 🎨 Design System

- **Dark Theme** - Deep blue-black background (#0A0E14)
- **Fighter Colors** - Red gradient vs Blue/Purple gradient
- **Accent Colors** - Yellow (#FACC15) for primary actions, Cyan (#06B6D4) for secondary
- **Typography** - Inter font family
- **Animations** - Smooth transitions and hover effects

## 📦 Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

## 🏗️ Project Structure

```
frontend-redesign/
├── src/
│   ├── components/
│   │   ├── dashboard/
│   │   │   ├── HeroFightCard.jsx      # Main event card
│   │   │   ├── QuickLinks.jsx          # Navigation cards
│   │   │   └── ...                     # More components to come
│   │   └── shared/
│   │       ├── Button.jsx              # Reusable button
│   │       └── Card.jsx                # Reusable card
│   ├── pages/
│   │   └── Dashboard.jsx               # Main dashboard page
│   ├── styles/
│   │   ├── design-system.js            # Design tokens
│   │   └── global.css                  # Global styles
│   ├── App.jsx
│   └── main.jsx
├── index.html
├── package.json
└── vite.config.js
```

## 🎯 Components Built

### ✅ Completed
- [x] Design System (colors, typography, spacing)
- [x] Global Styles (CSS variables, animations)
- [x] Button Component
- [x] Card Component
- [x] HeroFightCard (main event showcase)
- [x] QuickLinks (navigation grid)
- [x] Dashboard Page (main container)
- [x] News Ticker

### 🚧 To Build Next
- [ ] Hot Takes Section (controversial predictions)
- [ ] Upcoming Fights Grid
- [ ] Events Timeline
- [ ] Model Performance Chart
- [ ] Updates/Changelog Section
- [ ] Navbar/Header
- [ ] Footer

## 🔗 Connecting to Backend

The frontend is configured to proxy API calls to `localhost:8000`. Your existing FastAPI backend should work without changes.

Example API call:
```javascript
const response = await fetch('/api/fighters');
const fighters = await response.json();
```

## 🎨 Color Reference

```javascript
// Fighter colors
Red Corner: #FF4655 → #C9184A → #590D22
Blue Corner: #4F46E5 → #7C3AED → #2D1B69

// Accents
Primary CTA: #FACC15 (Yellow)
Secondary: #06B6D4 (Cyan)
Success: #84CC16 (Lime)
Warning: #F97316 (Orange)
Danger: #EF4444 (Red)

// Value Indicators (NEW!)
High Value: #84CC16
Medium Value: #FACC15
Low Value: #94A3B8
```

## 📝 Notes

- Uses Vite for fast dev server and build
- React 18 with hooks
- No external UI libraries - custom components
- Designed mobile-first, scales up
- All animations use CSS for performance

## 🔥 What Makes This Better Than FightSignal

1. **Value Bet Indicators** - Shows +/- % vs Vegas odds
2. **News Ticker** - Live updates at the top
3. **Hot Takes Section** - Highlights contrarian predictions
4. **Bet Calculator** - Helps users calculate stakes
5. **More Interactive** - Better hover effects, animations
6. **Cleaner Design** - Less clutter, better hierarchy

## 🚀 Next Steps

1. Build remaining dashboard components
2. Connect to real backend API
3. Add LLM integration for qualitative analysis
4. Implement news scraping
5. Add betting odds comparison
6. Build out Events and Signals pages
