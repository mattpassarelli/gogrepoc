import React, { useState, useEffect } from "react";
import {
  Container,
  Form,
  Button,
  Alert,
  ListGroup,
  Row,
  Col,
  Modal,
} from "react-bootstrap";
import axios from "axios";

// Add custom dark mode styles
const darkModeStyles = `
  .list-group-item {
    background-color: #2b3035;
    border-color: #373b3e;
    color: #e9ecef;
  }
  .list-group-item:hover {
    background-color: #343a40;
  }
  .list-group-item.active {
    background-color: #0d6efd;
    border-color: #0d6efd;
  }
  .list-group-item.disabled {
    background-color: #1a1d20;
    color: #6c757d;
  }
  .form-control {
    background-color: #2b3035;
    border-color: #373b3e;
    color: #e9ecef;
  }
  .form-control:focus {
    background-color: #2b3035;
    border-color: #565e64;
    color: #e9ecef;
  }
  .form-check-input {
    background-color: #2b3035;
    border-color: #373b3e;
  }
  .form-check-label {
    color: #e9ecef;
  }
`;

/**
 * Main App Component
 * 
 * @param {Object} props - Component props
 * @param {string} props.backendUrl - Backend API URL
 * @param {boolean} props.isElectron - Whether running in Electron
 * @param {boolean} props.backendAvailable - Whether backend is available
 * @param {string} props.backendError - Backend connection error message
 * 
 * Requirements: 7.2, 7.3, 7.5
 */
function App({ backendUrl, isElectron = false, backendAvailable = true, backendError = null }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [availableGames, setAvailableGames] = useState([]);
  const [downloadedGames, setDownloadedGames] = useState([]); // Already downloaded games from the server
  const [gamesToDownload, setGamesToDownload] = useState([]); // Games marked for download
  const [selectedAvailableGames, setSelectedAvailableGames] = useState([]);
  const [selectedToDownloadGames, setSelectedToDownloadGames] = useState([]);
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);
  const [downloading, setDownloading] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [savedir, setSavedir] = useState("C:/Games/GOG");
  const [compressDownloads, setCompressDownloads] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);
  const [selectedGamesToAdd, setSelectedGamesToAdd] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");

  /**
   * Handle directory selection using native dialog (Electron only)
   * Requirement 5.1: Display native dialog for directory selection
   */
  const handleSelectDirectory = async () => {
    if (isElectron && window.electronAPI && window.electronAPI.selectDirectory) {
      try {
        const selectedPath = await window.electronAPI.selectDirectory();
        if (selectedPath) {
          setSavedir(selectedPath);
        }
      } catch (error) {
        console.error('Failed to select directory:', error);
        setError('Failed to open directory selection dialog');
      }
    }
  };
  const [filterOS, setFilterOS] = useState("all");
  const [filterLang, setFilterLang] = useState("all");
  const [selectedGameForDetails, setSelectedGameForDetails] = useState(null);
  const [showGameDetailsModal, setShowGameDetailsModal] = useState(false);

  // Configure axios with dynamic backend URL
  useEffect(() => {
    if (backendUrl) {
      axios.defaults.baseURL = backendUrl;
      axios.defaults.withCredentials = true;
    }
  }, [backendUrl]);

  // Check authentication and load games list on component mount
  useEffect(() => {
    // Only check auth if backend is available
    if (backendAvailable) {
      checkAuth();
    } else if (backendError) {
      setError(`Backend unavailable: ${backendError}`);
    }
    
    // Load settings from localStorage
    const savedSavedir = localStorage.getItem("savedir");
    const savedCompress = localStorage.getItem("compressDownloads");
    const savedFilterOS = localStorage.getItem("filterOS");
    const savedFilterLang = localStorage.getItem("filterLang");
    
    if (savedSavedir) setSavedir(savedSavedir);
    if (savedCompress) setCompressDownloads(savedCompress === "true");
    if (savedFilterOS) setFilterOS(savedFilterOS);
    if (savedFilterLang) setFilterLang(savedFilterLang);
  }, [backendAvailable, backendError]);

  // Save settings to localStorage when they change
  useEffect(() => {
    localStorage.setItem("savedir", savedir);
  }, [savedir]);

  useEffect(() => {
    localStorage.setItem("compressDownloads", compressDownloads.toString());
  }, [compressDownloads]);

  useEffect(() => {
    localStorage.setItem("filterOS", filterOS);
  }, [filterOS]);

  useEffect(() => {
    localStorage.setItem("filterLang", filterLang);
  }, [filterLang]);

  const checkAuth = async () => {
    try {
      const response = await axios.get("/api/check-auth");
      if (response.data.authenticated) {
        setIsAuthenticated(true);
        fetchGames();
      }
    } catch (err) {
      setError("Not authenticated. Please login.");
      setIsAuthenticated(false);
    }
  };

  const fetchGames = async () => {
    try {
      setIsLoading(true);
      const response = await axios.get("/api/manifest");
      // New API returns games array with total_count
      const allGames = response.data.games || [];
      
      // Separate downloaded games from available games
      // For now, we'll need to track downloaded games separately
      // The manifest endpoint returns all games
      setAvailableGames(allGames);
      setDownloadedGames([]); // Will be populated from storage
      setSelectedToDownloadGames([]);
      setGamesToDownload([]);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to load games");
    } finally {
      setIsLoading(false);
    }
  };

  const handleMoveToDownload = () => {
    if (selectedAvailableGames.length === 0) return;

    setGamesToDownload([...gamesToDownload, ...selectedAvailableGames]);
    setAvailableGames(
      availableGames.filter(
        (game) =>
          !selectedAvailableGames.some((selected) => selected.id === game.id)
      )
    );
    setSelectedAvailableGames([]);

    // Sort games to download by title
    setGamesToDownload((prevGames) =>
      [...prevGames].sort((a, b) => a.title.localeCompare(b.title))
    );
  };

  const handleMoveToAvailable = () => {
    if (selectedToDownloadGames.length === 0) return;

    setAvailableGames([...availableGames, ...selectedToDownloadGames]);
    setGamesToDownload(
      gamesToDownload.filter(
        (game) =>
          !selectedToDownloadGames.some((selected) => selected.id === game.id)
      )
    );
    setSelectedToDownloadGames([]);

    // Sort available games by title
    setAvailableGames((prevGames) =>
      [...prevGames].sort((a, b) => a.title.localeCompare(b.title))
    );
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setError(null);
    setMessage(null);
    try {
      const response = await axios.post("/api/login", { username, password });
      if (response.data.success) {
        setMessage(response.data.message);
        // After successful login, check auth status and fetch games
        await checkAuth();
      } else {
        setError(response.data.message || "Login failed");
      }
    } catch (err) {
      setError(err.response?.data?.detail || "Login failed");
    }
  };

  const handleUpdate = async () => {
    try {
      setIsUpdating(true);
      setMessage("Updating game list. Please wait...");
      setError(null);
      const response = await axios.post("/api/update", {
        os_types: ["windows"], // You might want to make this configurable
        languages: ["en"],
      });
      setMessage(response.data.message);
      fetchGames(); // Refresh the games list
    } catch (err) {
      setError(err.response?.data?.detail || "Update failed");
    } finally {
      setIsUpdating(false);
    }
  };

  const handleAddWithoutDownload = async () => {
    try {
      const selectedIds = selectedGamesToAdd.map((game) => game.id);
      const response = await axios.post("/api/add_without_download", {
        game_ids: selectedIds,
        save_dir: savedir,
      });
      setMessage(response.data.message);
      fetchGames(); // Refresh the games list
      setShowAddModal(false);
      setSelectedGamesToAdd([]);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to add games");
    }
  };

  const handleDownload = async () => {
    try {
      setDownloading(true);
      setMessage("Starting download...");
      setError(null);

      const selectedIds = gamesToDownload.map((game) => game.id);

      const response = await axios.post("/api/download", {
        save_dir: savedir,
        os_types: ["windows"],
        languages: ["en"],
        game_ids: selectedIds,
        compress: compressDownloads,
      });
      
      if (response.data.success && response.data.task_id) {
        setMessage("Download started. Tracking progress...");
        // Start listening to progress updates via SSE
        listenToDownloadProgress(response.data.task_id);
      } else {
        setError("Failed to start download");
        setDownloading(false);
      }
    } catch (err) {
      setError(err.response?.data?.detail || "Download failed");
      setDownloading(false);
    }
  };

  const listenToDownloadProgress = (taskId) => {
    const eventSource = new EventSource(`${backendUrl}/api/download-progress/${taskId}`);
    
    eventSource.onmessage = (event) => {
      try {
        const progress = JSON.parse(event.data);
        
        // Update UI with progress information
        if (progress.current_game) {
          setMessage(
            `Downloading: ${progress.current_game} - ${progress.progress_percent.toFixed(1)}%`
          );
        }
        
        // Check if download is complete or failed
        if (progress.status === "completed") {
          setMessage("Download completed successfully!");
          setDownloading(false);
          eventSource.close();
          fetchGames(); // Refresh games list
        } else if (progress.status === "failed") {
          setError(progress.error || "Download failed");
          setDownloading(false);
          eventSource.close();
        }
      } catch (err) {
        console.error("Error parsing progress data:", err);
      }
    };
    
    eventSource.onerror = (err) => {
      console.error("SSE error:", err);
      setError("Lost connection to download progress");
      setDownloading(false);
      eventSource.close();
    };
  };

  // Filter games based on search term and filters
  const getFilteredGames = (games) => {
    return games.filter((game) => {
      // Search filter
      const matchesSearch = game.title
        .toLowerCase()
        .includes(searchTerm.toLowerCase());
      
      // OS filter (check if game has downloads for selected OS)
      const matchesOS =
        filterOS === "all" ||
        game.downloads.some((d) => d.os_type === filterOS);
      
      // Language filter (check if game has downloads for selected language)
      const matchesLang =
        filterLang === "all" ||
        game.downloads.some((d) => d.lang === filterLang);
      
      return matchesSearch && matchesOS && matchesLang;
    });
  };

  // Calculate total download size for selected games
  const calculateTotalSize = (games) => {
    let totalBytes = 0;
    games.forEach((game) => {
      game.downloads.forEach((download) => {
        totalBytes += download.size || 0;
      });
      game.extras.forEach((extra) => {
        totalBytes += extra.size || 0;
      });
    });
    return totalBytes;
  };

  // Format bytes to human-readable size
  const formatBytes = (bytes) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB", "TB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + " " + sizes[i];
  };

  // Calculate estimated download time (assuming 10 MB/s average speed)
  const calculateEstimatedTime = (bytes) => {
    const avgSpeedBytesPerSec = 10 * 1024 * 1024; // 10 MB/s
    const seconds = bytes / avgSpeedBytesPerSec;
    
    if (seconds < 60) {
      return `${Math.round(seconds)} seconds`;
    } else if (seconds < 3600) {
      return `${Math.round(seconds / 60)} minutes`;
    } else {
      const hours = Math.floor(seconds / 3600);
      const minutes = Math.round((seconds % 3600) / 60);
      return `${hours}h ${minutes}m`;
    }
  };

  // Show game details modal
  const showGameDetails = (game) => {
    setSelectedGameForDetails(game);
    setShowGameDetailsModal(true);
  };

  useEffect(() => {
    // Set dark theme on body when component mounts
    document.body.setAttribute("data-bs-theme", "dark");
    return () => {
      // Clean up when component unmounts
      document.body.removeAttribute("data-bs-theme");
    };
  }, []);

  return (
    <Container className="mt-5">
      <style>{darkModeStyles}</style>
      <h1 className="text-light">GOG Installers Downloader</h1>

      {/* Backend unavailable state */}
      {!backendAvailable && (
        <Alert variant="warning" className="mt-4">
          <Alert.Heading>Backend Connection Issue</Alert.Heading>
          <p>
            {isElectron 
              ? "The application backend is starting up or unavailable. Please wait..."
              : "Cannot connect to the backend server. Please ensure the server is running."}
          </p>
          {backendError && (
            <p className="mb-0">
              <strong>Error:</strong> {backendError}
            </p>
          )}
          <div className="mt-3">
            <Button 
              variant="outline-warning" 
              onClick={() => window.location.reload()}
            >
              Retry Connection
            </Button>
          </div>
        </Alert>
      )}

      {error && (
        <Alert variant="danger" dismissible>
          {error}
        </Alert>
      )}
      {message && (
        <Alert variant="success" dismissible>
          {message}
        </Alert>
      )}

      {!isAuthenticated && backendAvailable && (
        <Form onSubmit={handleLogin} className="mb-4">
          <Form.Group className="mb-3">
            <Form.Label>GOG Email</Form.Label>
            <Form.Control
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </Form.Group>

          <Form.Group className="mb-3">
            <Form.Label>Password</Form.Label>
            <Form.Control
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </Form.Group>

          <Button type="submit">Login</Button>
        </Form>
      )}
      {isAuthenticated && backendAvailable && (
        <>
          {/* Search and Filter Controls */}
          <Row className="mt-3 mb-3">
            <Col md={4}>
              <Form.Group>
                <Form.Label>Search Games</Form.Label>
                <Form.Control
                  type="text"
                  placeholder="Search by title..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
              </Form.Group>
            </Col>
            <Col md={3}>
              <Form.Group>
                <Form.Label>Filter by OS</Form.Label>
                <Form.Select
                  value={filterOS}
                  onChange={(e) => setFilterOS(e.target.value)}
                >
                  <option value="all">All OS</option>
                  <option value="windows">Windows</option>
                  <option value="linux">Linux</option>
                  <option value="mac">Mac</option>
                </Form.Select>
              </Form.Group>
            </Col>
            <Col md={3}>
              <Form.Group>
                <Form.Label>Filter by Language</Form.Label>
                <Form.Select
                  value={filterLang}
                  onChange={(e) => setFilterLang(e.target.value)}
                >
                  <option value="all">All Languages</option>
                  <option value="en">English</option>
                  <option value="de">German</option>
                  <option value="fr">French</option>
                  <option value="es">Spanish</option>
                </Form.Select>
              </Form.Group>
            </Col>
            <Col md={2} className="d-flex align-items-end">
              <Button
                onClick={() => {
                  setSearchTerm("");
                  setFilterOS("all");
                  setFilterLang("all");
                }}
                variant="secondary"
                className="w-100"
              >
                Clear Filters
              </Button>
            </Col>
          </Row>

          <Row className="mt-4">
            <Col>
              <h4>{`Available Games (${getFilteredGames(availableGames).length})`}</h4>
              {isLoading ? (
                <div className="text-center p-4">
                  <div className="spinner-border text-primary" role="status">
                    <span className="visually-hidden">Loading...</span>
                  </div>
                  <p className="mt-2">Loading games...</p>
                </div>
              ) : (
                <ListGroup style={{ height: "400px", overflow: "auto" }}>
                  {getFilteredGames(availableGames).map((game) => (
                    <ListGroup.Item
                      key={game.id}
                      active={selectedAvailableGames.some(
                        (selected) => selected.id === game.id
                      )}
                      action
                      onClick={() => {
                        const isSelected = selectedAvailableGames.some(
                          (selected) => selected.id === game.id
                        );
                        if (isSelected) {
                          setSelectedAvailableGames(
                            selectedAvailableGames.filter(
                              (selected) => selected.id !== game.id
                            )
                          );
                        } else {
                          setSelectedAvailableGames([
                            ...selectedAvailableGames,
                            game,
                          ]);
                        }
                      }}
                      onDoubleClick={() => showGameDetails(game)}
                      title="Double-click to view details"
                    >
                      {game.title}
                    </ListGroup.Item>
                  ))}
                </ListGroup>
              )}
            </Col>

            <Col
              xs="auto"
              className="d-flex flex-column justify-content-center gap-2"
            >
              <Button
                onClick={handleMoveToDownload}
                disabled={selectedAvailableGames.length === 0}
              >
                &gt;&gt;
              </Button>
              <Button
                onClick={handleMoveToAvailable}
                disabled={selectedToDownloadGames.length === 0}
              >
                &lt;&lt;
              </Button>
            </Col>

            <Col>
              <h4>Games Queue</h4>
              <div className="mb-2">
                <h6>To Download</h6>
                <ListGroup style={{ height: "200px", overflow: "auto" }}>
                  {gamesToDownload.map((game) => (
                    <ListGroup.Item
                      key={game.id}
                      active={selectedToDownloadGames.some(
                        (selected) => selected.id === game.id
                      )}
                      action
                      onClick={() => {
                        const isSelected = selectedToDownloadGames.some(
                          (selected) => selected.id === game.id
                        );
                        if (isSelected) {
                          setSelectedToDownloadGames(
                            selectedToDownloadGames.filter(
                              (selected) => selected.id !== game.id
                            )
                          );
                        } else {
                          setSelectedToDownloadGames([
                            ...selectedToDownloadGames,
                            game,
                          ]);
                        }
                      }}
                    >
                      {game.title}
                    </ListGroup.Item>
                  ))}
                </ListGroup>
              </div>

              <div>
                <div className="d-flex justify-content-between align-items-center mb-2">
                  <h6 className="m-0">{`Already Downloaded (${downloadedGames.length})⬇️`}</h6>
                  <span
                    className="text-muted"
                    style={{
                      cursor: "pointer",
                      fontSize: "0.9em",
                      transition: "all 0.2s ease",
                      ":hover": { textDecoration: "underline" },
                    }}
                    onMouseEnter={(e) =>
                      (e.target.style.textDecoration = "underline")
                    }
                    onMouseLeave={(e) =>
                      (e.target.style.textDecoration = "none")
                    }
                    onClick={() => setShowAddModal(true)}
                  >
                    Need to add games to this list?
                  </span>
                </div>

                <Modal
                  show={showAddModal}
                  onHide={() => {
                    setShowAddModal(false);
                    setSelectedGamesToAdd([]);
                  }}
                  size="lg"
                >
                  <Modal.Header closeButton>
                    <Modal.Title>Add Games to Downloaded List</Modal.Title>
                  </Modal.Header>
                  <Modal.Body>
                    <p className="text-muted mb-3">
                      Select games that you've already downloaded to add them to
                      your downloaded games list.
                    </p>
                    <ListGroup style={{ maxHeight: "400px", overflow: "auto" }}>
                      {availableGames.map((game) => (
                        <ListGroup.Item
                          key={game.id}
                          action
                          active={selectedGamesToAdd.some(
                            (selected) => selected.id === game.id
                          )}
                          onClick={() => {
                            const isSelected = selectedGamesToAdd.some(
                              (selected) => selected.id === game.id
                            );
                            if (isSelected) {
                              setSelectedGamesToAdd(
                                selectedGamesToAdd.filter(
                                  (selected) => selected.id !== game.id
                                )
                              );
                            } else {
                              setSelectedGamesToAdd([
                                ...selectedGamesToAdd,
                                game,
                              ]);
                            }
                          }}
                        >
                          {game.title}
                        </ListGroup.Item>
                      ))}
                    </ListGroup>
                  </Modal.Body>
                  <Modal.Footer>
                    <Button
                      variant="secondary"
                      onClick={() => {
                        setShowAddModal(false);
                        setSelectedGamesToAdd([]);
                      }}
                    >
                      Cancel
                    </Button>
                    <Button
                      variant="primary"
                      onClick={handleAddWithoutDownload}
                      disabled={selectedGamesToAdd.length === 0}
                    >
                      Add Selected Games ({selectedGamesToAdd.length})
                    </Button>
                  </Modal.Footer>
                </Modal>

                <ListGroup style={{ height: "200px", overflow: "auto" }}>
                  {downloadedGames.map((game) => (
                    <ListGroup.Item key={game.id} disabled>
                      {game.title}
                    </ListGroup.Item>
                  ))}
                </ListGroup>
              </div>
            </Col>
          </Row>

          <Row className="mt-4">
            <div style={{ display: "flex", justifyContent: "space-evenly" }}>
              <Button 
                onClick={handleUpdate} 
                variant="info"
                disabled={isUpdating}
              >
                {isUpdating ? (
                  <>
                    <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                    Updating...
                  </>
                ) : (
                  "Update List"
                )}
              </Button>
              <div className="d-flex align-items-center gap-2">
                <span>Download Path:</span>
                {isElectron ? (
                  // Electron mode: Use native dialog with button and read-only display
                  <>
                    <Form.Group style={{ width: "300px" }} className="m-0">
                      <Form.Control
                        type="text"
                        value={savedir}
                        readOnly
                        placeholder="No directory selected"
                        title={savedir}
                      />
                    </Form.Group>
                    <Button
                      variant="outline-primary"
                      size="sm"
                      onClick={handleSelectDirectory}
                      title="Select download directory"
                    >
                      Browse...
                    </Button>
                  </>
                ) : (
                  // Web mode: Use text input for manual entry
                  <Form.Group style={{ width: "300px" }} className="m-0">
                    <Form.Control
                      type="text"
                      value={savedir}
                      onChange={(e) => setSavedir(e.target.value)}
                      placeholder="Enter download path (e.g., C:/Games/GOG)"
                    />
                  </Form.Group>
                )}
              </div>
              <div>
                <div className="d-flex flex-column gap-2">
                  {gamesToDownload.length > 0 && (
                    <div className="text-muted small mb-2">
                      <div>Total Size: {formatBytes(calculateTotalSize(gamesToDownload))}</div>
                      <div>Est. Time: {calculateEstimatedTime(calculateTotalSize(gamesToDownload))}</div>
                    </div>
                  )}
                  <Button
                    onClick={handleDownload}
                    variant="success"
                    disabled={downloading || gamesToDownload.length === 0}
                  >
                    {downloading ? (
                      <>
                        <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                        Downloading...
                      </>
                    ) : (
                      `Download Games (${gamesToDownload.length})`
                    )}
                  </Button>
                  <Form.Check
                    type="checkbox"
                    id="compress-downloads"
                    label="Compress downloads?"
                    checked={compressDownloads}
                    onChange={(e) => setCompressDownloads(e.target.checked)}
                  />
                </div>
              </div>
            </div>
          </Row> 
        </>
      )}

      {/* Game Details Modal */}
      <Modal
        show={showGameDetailsModal}
        onHide={() => {
          setShowGameDetailsModal(false);
          setSelectedGameForDetails(null);
        }}
        size="lg"
      >
        <Modal.Header closeButton>
          <Modal.Title>
            {selectedGameForDetails?.title || "Game Details"}
          </Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {selectedGameForDetails && (
            <>
              {/* Game Images */}
              {selectedGameForDetails.image_url && (
                <div className="text-center mb-3">
                  <img
                    src={selectedGameForDetails.image_url}
                    alt={selectedGameForDetails.title}
                    style={{ maxWidth: "100%", maxHeight: "300px" }}
                    onError={(e) => {
                      e.target.style.display = "none";
                    }}
                  />
                </div>
              )}

              {/* Game Info */}
              <div className="mb-3">
                <h6>Title:</h6>
                <p>{selectedGameForDetails.long_title || selectedGameForDetails.title}</p>
              </div>

              {/* Store Link */}
              {selectedGameForDetails.store_url && (
                <div className="mb-3">
                  <a
                    href={selectedGameForDetails.store_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn btn-sm btn-outline-primary"
                  >
                    View on GOG Store
                  </a>
                </div>
              )}

              {/* Changelog */}
              {selectedGameForDetails.changelog && (
                <div className="mb-3">
                  <h6>Changelog:</h6>
                  <div
                    style={{
                      maxHeight: "200px",
                      overflow: "auto",
                      backgroundColor: "#2b3035",
                      padding: "10px",
                      borderRadius: "5px",
                    }}
                  >
                    <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>
                      {selectedGameForDetails.changelog}
                    </pre>
                  </div>
                </div>
              )}

              {/* Downloads */}
              {selectedGameForDetails.downloads && selectedGameForDetails.downloads.length > 0 && (
                <div className="mb-3">
                  <h6>Available Downloads ({selectedGameForDetails.downloads.length}):</h6>
                  <ListGroup style={{ maxHeight: "200px", overflow: "auto" }}>
                    {selectedGameForDetails.downloads.map((download, idx) => (
                      <ListGroup.Item key={idx}>
                        <div>
                          <strong>{download.name}</strong>
                        </div>
                        <div className="small text-muted">
                          {download.os_type} | {download.lang} | {formatBytes(download.size)}
                          {download.version && ` | v${download.version}`}
                        </div>
                        {download.desc && (
                          <div className="small">{download.desc}</div>
                        )}
                      </ListGroup.Item>
                    ))}
                  </ListGroup>
                </div>
              )}

              {/* Extras */}
              {selectedGameForDetails.extras && selectedGameForDetails.extras.length > 0 && (
                <div className="mb-3">
                  <h6>Extras ({selectedGameForDetails.extras.length}):</h6>
                  <ListGroup style={{ maxHeight: "150px", overflow: "auto" }}>
                    {selectedGameForDetails.extras.map((extra, idx) => (
                      <ListGroup.Item key={idx}>
                        <div>
                          <strong>{extra.name}</strong>
                        </div>
                        <div className="small text-muted">
                          {formatBytes(extra.size)}
                          {extra.desc && ` | ${extra.desc}`}
                        </div>
                      </ListGroup.Item>
                    ))}
                  </ListGroup>
                </div>
              )}

              {/* Serials */}
              {selectedGameForDetails.serials && Object.keys(selectedGameForDetails.serials).length > 0 && (
                <div className="mb-3">
                  <h6>Serial Keys:</h6>
                  <div
                    style={{
                      backgroundColor: "#2b3035",
                      padding: "10px",
                      borderRadius: "5px",
                    }}
                  >
                    {Object.entries(selectedGameForDetails.serials).map(([key, value]) => (
                      <div key={key}>
                        <strong>{key}:</strong> {value}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </Modal.Body>
        <Modal.Footer>
          <Button
            variant="secondary"
            onClick={() => {
              setShowGameDetailsModal(false);
              setSelectedGameForDetails(null);
            }}
          >
            Close
          </Button>
        </Modal.Footer>
      </Modal>
    </Container>
  );
}

export default App;
