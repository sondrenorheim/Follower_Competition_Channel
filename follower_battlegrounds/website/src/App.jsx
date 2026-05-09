import { useEffect } from 'react';
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import Header from './components/Header';
import DailyResults from './pages/DailyResults';
import MonthlyRankings from './pages/MonthlyRankings';
import PlayerProfile from './pages/PlayerProfile';
import MediaKit from './pages/MediaKit';
import Privacy from './pages/Privacy';
import HallOfFame from './pages/HallOfFame';
import MemberClub from './pages/MemberClub';

function AppContent() {
  const location = useLocation();
  const hideHeader = location.pathname === '/mediakit' || location.pathname === '/privacy';

  // Track page views on route changes for Google Analytics
  useEffect(() => {
    if (!window.gtag) return;
    window.gtag('event', 'page_view', {
      page_path: location.pathname + location.search,
      page_location: window.location.href,
    });
  }, [location]);

  return (
    <div className="min-h-screen bg-dark-bg-primary">
      {!hideHeader && <Header />}
      <Routes>
        <Route path="/" element={<DailyResults />} />
        <Route path="/monthly" element={<MonthlyRankings />} />
        <Route path="/hall-of-fame" element={<HallOfFame />} />
        <Route path="/member-club" element={<MemberClub />} />
        <Route path="/player/:username" element={<PlayerProfile />} />
        <Route path="/mediakit" element={<MediaKit />} />
        <Route path="/privacy" element={<Privacy />} />
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
