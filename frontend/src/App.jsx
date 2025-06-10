// frontend/src/App.jsx
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import HomePage from './pages/HomePage';
import AdminPage from './pages/AdminPage';

function App() {
  return (
    <Router>
      <div className="app">
        <header className="app-header">
          <h1>
            <Link to="/" style={{ textDecoration: 'none', color: 'inherit' }}>
              !Shazam
            </Link>
          </h1>
          <nav className="app-nav">
            <Link to="/admin">Manage Songs</Link>
          </nav>
        </header>

        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/admin" element={<AdminPage />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;