import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import Header from './components/Header';
import DailyResults from './pages/DailyResults';
import MonthlyRankings from './pages/MonthlyRankings';
import PlayerProfile from './pages/PlayerProfile';
import MediaKit from './pages/MediaKit';

function AppContent() {
  const location = useLocation();
  const hideHeader = location.pathname === '/mediakit';

  return (
    <div className="min-h-screen bg-dark-bg-primary">
      {!hideHeader && <Header />}
      <Routes>
        <Route path="/" element={<DailyResults />} />
        <Route path="/monthly" element={<MonthlyRankings />} />
        <Route path="/player/:username" element={<PlayerProfile />} />
        <Route path="/mediakit" element={<MediaKit />} />
      </Routes>
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AppContent />
    </BrowserRouter>
  );
}

export default App;
