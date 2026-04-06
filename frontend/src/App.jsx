import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Navbar from './components/layout/Navbar';
import Footer from './components/layout/Footer';
import Dashboard from './pages/Dashboard';
import FighterSearch from './pages/FighterSearch';
import FighterProfile from './pages/FighterProfile';
import PicksBuilder from './pages/PicksBuilder';
import HistoricalScorecard from './pages/HistoricalScorecard';
import './styles/global.css';

function App() {
  return (
    <Router>
      <div className="App">
        <Navbar />
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/fighters" element={<FighterSearch />} />
          <Route path="/fighter/:name" element={<FighterProfile />} />
          <Route path="/picks" element={<PicksBuilder />} />
          <Route path="/scorecard" element={<HistoricalScorecard />} />
        </Routes>
        <Footer />
      </div>
    </Router>
  );
}

export default App;