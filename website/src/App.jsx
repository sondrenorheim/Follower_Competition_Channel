import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Header from './components/Header';
import DailyResults from './pages/DailyResults';
import MonthlyRankings from './pages/MonthlyRankings';
import PlayerProfile from './pages/PlayerProfile';

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-100">
        <Header />
        <Routes>
          <Route path="/" element={<DailyResults />} />
          <Route path="/monthly" element={<MonthlyRankings />} />
          <Route path="/player/:username" element={<PlayerProfile />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

export default App;
