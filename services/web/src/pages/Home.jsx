import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { apiFetch } from "../api";

export default function Home() {
  const [videos, setVideos] = useState([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    setLoading(true);
    const params = search ? `?search=${encodeURIComponent(search)}` : "";
    apiFetch(`/api/videos/videos${params}`)
      .then((r) => r.json())
      .then((data) => {
        setVideos(data.videos || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [search]);

  return (
    <div className="page home-page">
      <h1>Videos</h1>
      <input
        type="text"
        className="search-input"
        placeholder="Search videos..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />
      {loading ? (
        <p className="status-text">Loading...</p>
      ) : videos.length === 0 ? (
        <p className="status-text">No videos found.</p>
      ) : (
        <ul className="video-list">
          {videos.map((v) => (
            <li
              key={v.id}
              className="video-item"
              onClick={() =>
                navigate(`/videos/${v.id}`, { state: { video: v } })
              }
            >
              <span className="video-name">{v.name}</span>
              <span className="video-year">{v.year}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
