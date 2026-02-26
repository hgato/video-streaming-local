import { useState, useEffect, useRef } from "react";
import { useParams, useLocation, useNavigate } from "react-router-dom";
import Hls from "hls.js";
import { apiFetch } from "../api";

export default function Video({ socket }) {
  const { id } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const [video, setVideo] = useState(location.state?.video || null);
  const [checking, setChecking] = useState(true);
  const [preparing, setPreparing] = useState(false);
  const [manifestUrl, setManifestUrl] = useState(null);
  const [levels, setLevels] = useState([]);
  const [currentLevel, setCurrentLevel] = useState(-1);
  const videoRef = useRef(null);
  const hlsRef = useRef(null);

  useEffect(() => {
    if (video) return;
    apiFetch("/api/videos/videos")
      .then((r) => r.json())
      .then((data) => {
        const found = (data.videos || []).find((v) => v.id === id);
        if (found) setVideo(found);
      });
  }, [id, video]);

  useEffect(() => {
    apiFetch(`/api/videos/videos/${id}/status`)
      .then((r) => r.json())
      .then((data) => {
        if (data.ready && data.manifest_url) {
          setManifestUrl(data.manifest_url);
        }
      })
      .catch(() => {})
      .finally(() => setChecking(false));
  }, [id]);

  useEffect(() => {
    if (!socket) return;
    const handler = (data) => {
      if (data.video_id === id) {
        setManifestUrl(data.manifest_url);
        setPreparing(false);
      }
    };
    socket.on("video:ready", handler);
    return () => socket.off("video:ready", handler);
  }, [socket, id]);

  useEffect(() => {
    if (!manifestUrl || !videoRef.current) return;

    if (Hls.isSupported()) {
      const hls = new Hls();
      hlsRef.current = hls;
      hls.loadSource(manifestUrl);
      hls.attachMedia(videoRef.current);
      hls.on(Hls.Events.MANIFEST_PARSED, (_, data) => {
        setLevels(data.levels);
        setCurrentLevel(-1);
      });
      hls.on(Hls.Events.LEVEL_SWITCHED, (_, data) => {
        setCurrentLevel(data.level);
      });
      return () => {
        hls.destroy();
        hlsRef.current = null;
      };
    } else if (videoRef.current.canPlayType("application/vnd.apple.mpegurl")) {
      videoRef.current.src = manifestUrl;
    }
  }, [manifestUrl]);

  function handleQualityChange(levelIndex) {
    if (!hlsRef.current) return;
    hlsRef.current.currentLevel = levelIndex;
    setCurrentLevel(levelIndex);
  }

  async function handlePrepare() {
    setPreparing(true);
    try {
      const res = await apiFetch(`/api/videos/videos/${id}/prepare`, {
        method: "POST",
      });
      if (!res.ok) setPreparing(false);
    } catch {
      setPreparing(false);
    }
  }

  return (
    <div className="page video-page">
      <button className="back-btn" onClick={() => navigate("/")}>
        &larr; Back
      </button>
      <h1>{video ? `${video.name} (${video.year})` : "Loading..."}</h1>

      {!manifestUrl && (
        <div className="prepare-section">
          {checking ? (
            <p className="status-text">Checking status...</p>
          ) : (
            <>
              <p>This video needs to be prepared for streaming.</p>
              <button onClick={handlePrepare} disabled={preparing}>
                {preparing ? "Preparing..." : "Prepare Video"}
              </button>
              {preparing && (
                <p className="preparing-notice">
                  Processing video — you will be notified when it is ready.
                </p>
              )}
            </>
          )}
        </div>
      )}

      {manifestUrl && (
        <div className="player-section">
          {levels.length > 0 && (
            <div className="quality-selector">
              <span className="quality-label">Quality:</span>
              <button
                className={currentLevel === -1 ? "quality-btn active" : "quality-btn"}
                onClick={() => handleQualityChange(-1)}
              >
                Auto
              </button>
              {levels.map((level, i) => (
                <button
                  key={i}
                  className={currentLevel === i ? "quality-btn active" : "quality-btn"}
                  onClick={() => handleQualityChange(i)}
                >
                  {level.height ? `${level.height}p` : `${Math.round(level.bitrate / 1000)}k`}
                </button>
              ))}
            </div>
          )}
          <video ref={videoRef} controls className="video-player" />
        </div>
      )}
    </div>
  );
}
