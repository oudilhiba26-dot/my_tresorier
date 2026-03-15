# Frontend Structure (To Be Implemented)

```
frontend/
├── index.html                   # Main HTML file
├── package.json                 # npm dependencies
├── vite.config.js              # Vite configuration
├── tailwind.config.js          # Tailwind CSS config
│
├── src/
│   ├── main.jsx                # Entry point
│   ├── App.jsx                 # Main App component
│   ├── index.css               # Global styles
│   │
│   ├── components/             # Reusable components
│   │   ├── Header.jsx
│   │   ├── Navigation.jsx
│   │   ├── BudgetForm.jsx
│   │   ├── BudgetChart.jsx
│   │   └── PriceTable.jsx
│   │
│   ├── pages/                  # Page components
│   │   ├── LandingPage.jsx
│   │   ├── DashboardPage.jsx
│   │   └── ResultsPage.jsx
│   │
│   ├── services/               # API communication
│   │   └── api.js             # Fetch calls to backend
│   │
│   └── store/                  # State management (if needed)
│       └── budgetStore.js
```

## Frontend Technologies

- **React 18** with Vite (fast build tool)
- **Tailwind CSS** (utility-first styling)
- **Chart.js** (price and budget visualizations)
- **Axios or Fetch API** (communicate with FastAPI backend)

## Next Steps

After testing the backend scrapers, we'll create:
1. Landing page with project description
2. Interactive form to enter budget and priorities
3. Dashboard with budget breakdown and price charts
4. Responsive mobile design using Tailwind CSS
