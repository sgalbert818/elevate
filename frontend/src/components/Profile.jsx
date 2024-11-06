import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faArrowUpRightFromSquare, faX, faPlay, faPause } from '@fortawesome/free-solid-svg-icons';

function Profile() {
  const [username, setUsername] = useState('');
  const navigate = useNavigate();
  const [artists, setArtists] = useState([])
  const [tracks, setTracks] = useState([])
  const [playlist, setPlaylist] = useState([])
  const [backups, setBackups] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [loadingMessage, setLoadingMessage] = useState('Crafting the ultimate playlist...');
  const [currentPlaying, setCurrentPlaying] = useState(null);

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const response = await fetch('https://18.218.68.142:5001/profile', {
          method: 'GET',
          credentials: 'include'
        });

        if (!response.ok) {
          // Handle non-2xx response
          const errorData = await response.json();
          throw new Error(errorData.message || 'Failed to fetch profile');
        }
        const data = await response.json();
        if (data && data.profile) {
          setUsername(data.profile.display_name);
          setArtists(data.top_artists.items.slice(0, 5)); // Get top 5 artists
          setTracks(data.top_tracks.items.slice(0, 5)); // Get top 5 tracks
        } else {
          navigate('/'); // Redirect if data is not present
        }
      } catch (error) {
        console.error(error);
        alert(error)
      }
    };
    fetchProfile();
  }, [navigate]);

  const phrases = ['Tuning into your vibes...',
    'Pulling listening history...',
    'Scanning tracks for hidden gems...',
    'Analyzing artists and influences...',
    'Finding the groove...',
    'Counting beats per minute...',
    'Matching your mood...',
    'Handpicking top tracks...',
    'Curating the perfect mix...',
    'Spinning records in the cloud...',
    'Filtering out any skips...',
    'Fetching your top anthems...',
    'Crafting the ultimate playlist...'
  ];

  // Start the loading cycle when loading is true
  useEffect(() => {
    if (loading) {
      let index = 0;
      const interval = setInterval(() => {
        setLoadingMessage(phrases[index]);
        index = (index + 1) % phrases.length; // Cycle through phrases
      }, 2000); // Change message every 2 seconds

      return () => clearInterval(interval); // Clear interval on cleanup
    }
  }, [loading]);

  const handleSignOut = () => {
    stopCurrentAudio()
    fetch('https://18.218.68.142:5001/logout', {
      method: 'GET',
      credentials: 'include',
    })
      .then(response => {
        if (response.ok) {
          window.location.href = 'https://main.d30okcwstuwyij.amplifyapp.com/';
        } else {
          return response.json().then(errorData => {
            throw new Error(errorData.message || 'Logout failed.');
          });
        }
      })
      .catch(error => {
        console.error(error);
        alert(error)
      });
  };

  const [formData, setFormData] = useState({
    //playlistName: '',
    playlistDuration: '30',
    activity: 'workout',
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prevData) => ({
      ...prevData,
      [name]: value,
    }));
  };

  const createPlaylist = (e) => {
    stopCurrentAudio()
    e.preventDefault();
    setError('');
    setLoading(true);
    fetch('https://18.218.68.142:5001/recommendations', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ ...formData }),
      credentials: 'include',
    })
      .then(response => {
        if (!response.ok) {
          // Handle non-2xx responses
          return response.json().then(errorData => {
            throw new Error(errorData.message || 'Failed to create playlist.');
          });
        }
        return response.json(); // If response is ok, parse the JSON
      })
      .then(data => {
        //console.log(data)
        setPlaylist(data.slice(0, Math.ceil(formData.playlistDuration / 4)));
        setBackups(data.slice(Math.ceil(formData.playlistDuration / 4)));
      })
      .catch(error => {
        //setError(error.message);
        console.error(error);
        alert(error)
      })
      .finally(() => {
        setLoading(false); // Always set loading to false in the end
      });
  };


  const deleteSong = (id) => {
    if (currentPlaying?.trackId === id) {
      currentPlaying.audio.pause(); // Stop the audio
      setCurrentPlaying(null); // Clear the current playing state
    }
    if (backups.length > 0) {
      setPlaylist((prev) => {
        const updatedPlaylist = prev.filter((each) => each.id !== id);
        return [...updatedPlaylist, backups[0]];
      });
      setBackups((prev) => prev.slice(1));
    } else {
      setError('No songs left for this query. Add playlist to library or make a new query and start again.')
    }
  };

  const [nameData, setNameData] = useState({
    playlistName: ''
  });

  const handleNameChange = (e) => {
    const { name, value } = e.target;
    setNameData((prevData) => ({
      ...prevData,
      [name]: value,
    }));
  };

  const deployPlaylist = (e) => {
    stopCurrentAudio()
    e.preventDefault();
    const myPlaylist = playlist.map(item => item.uri);
    fetch('https://18.218.68.142:5001/build', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ name: nameData.playlistName, songs: myPlaylist }),
      credentials: 'include'
    })
      .then(response => {
        if (!response.ok) {
          // Handle non-2xx responses
          return response.json().then(errorData => {
            throw new Error(errorData.message || 'Failed to deploy playlist.');
          });
        }
        return response.json(); // Parse the JSON if response is ok
      })
      .then(data => {
        //console.log(data); // Log success response
        setPlaylist([]);
        setBackups([]);
        setNameData({ playlistName: '' });
        setError('Playlist Successfully Created!');
      })
      .catch(error => {
        console.error('Error deploying playlist:', error);
        setError(error.message);
      });
  };

  const playPreview = (previewUrl, trackId) => {
    if (currentPlaying?.audio) {
      currentPlaying.audio.pause();
      setCurrentPlaying(null);
    }
    const audio = new Audio(previewUrl);
    audio.play();
    setCurrentPlaying({ audio, trackId });
    audio.addEventListener('ended', () => {
      setCurrentPlaying(null);
    });
  };

  const handlePlayPauseClick = (song) => {
    if (song.preview_url) {
      if (currentPlaying?.trackId === song.id) {
        currentPlaying.audio.pause();
        setCurrentPlaying(null);
      } else {
        playPreview(song.preview_url, song.id);
      }
    }
  };

  const stopCurrentAudio = () => {
    if (currentPlaying?.audio) {
      currentPlaying.audio.pause(); // Stop the audio
      setCurrentPlaying(null); // Clear the current playing state
    }
  };

  return (
    <div className="app">
      <div className="app-header mb10">
        {<h1>Welcome, {username ? username : 'Guest'}</h1>}
        <button onClick={handleSignOut}>Sign Out</button>
      </div>
      <h3 className="mb10">User Snapshot</h3>
      <div className="summary mb10">
        <div className="half mr10">
          <p className="mb10">Your Top 5 Tracks</p>
          {tracks.length > 0 && tracks.map((track) => {
            return <div key={track.id} className="ss song">
              <img src={track.album.images[2].url}></img>
              <p className="mr10">{track.name} by {track.artists[0].name}</p>
              <a href={track.external_urls.spotify} target="_blank"><FontAwesomeIcon icon={faArrowUpRightFromSquare} /></a>
            </div>
          })}
          {tracks.length < 1 && <p>Loading Tracks...</p>}
        </div>
        <div className="half">
          <p className="mb10">Your Top 5 Artists</p>
          {artists.length > 0 && artists.map((artist) => {
            return <div key={artist.id} className="ss song">
              <img src={artist.images[2].url}></img>
              <p className="mr10">{artist.name}</p>
              <a href={artist.external_urls.spotify} target="_blank"><FontAwesomeIcon icon={faArrowUpRightFromSquare} /></a>
            </div>
          })}
          {artists.length < 1 && <p>Loading Artists...</p>}
        </div>
      </div>
      <h3 className="mb10">Generate New Activity Playlist</h3>
      <div className="form">
        <form onSubmit={createPlaylist}>
          <div>
            <label htmlFor="playlistDuration" className="mr10">Playlist Duration:</label>
            <select
              className="mb10"
              id="playlistDuration"
              name="playlistDuration"
              value={formData.playlistDuration}
              onChange={handleChange}
              required
            >
              <option value="30">30 minutes</option>
              <option value="60">1 hour</option>
              <option value="120">2 hours</option>
              <option value="180">3 hours</option>
              <option value="240">4 hours</option>
            </select>
          </div>

          <div className="activities">
            <p className="mb10">Activity:</p>
            {['workout', 'relaxation', 'road_trip', 'party', 'focus', 'cooking', 'cleaning', 'date_night'].map((activityOption) => (
              <label key={activityOption} className="mr10 mb10 label">
                <input
                  type="radio"
                  name="activity"
                  value={activityOption}
                  checked={formData.activity === activityOption}
                  onChange={handleChange}
                  required
                />
                <p>
                  {activityOption.charAt(0).toUpperCase() + activityOption.slice(1).replace('_', ' ')}
                </p>
              </label>
            ))}
          </div>

          <button type="submit">Create Playlist</button>
        </form>
        <div className="formjr">
          {loading && <p className="mb10 mt5">{loadingMessage}</p>}
          {error && <p className="mb10 mt5">{error}</p>}
          {!loading && playlist.length > 0 && <div>
            <form onSubmit={deployPlaylist} className="mb10 add-playlist">
              <div id="pnl">
                <label htmlFor="playlistName" className="mr10">Playlist Name:</label>
                <input
                  className="mb10"
                  type="text"
                  id="playlistName"
                  name="playlistName"
                  value={nameData.playlistName}
                  onChange={handleNameChange}
                  required
                />
              </div>
              <button type="submit">Add playlist to Spotify Library</button>
            </form>
            {playlist.map((song) => {
              //console.log(song)
              return <div key={song.id} className="song">
                <img src={song.album.images[2].url}></img>
                <p>{song.name} by {song.artists[0].name}</p>
                <div className="prev">
                  {song.preview_url ? (
                    <>
                      <button id="play-pause" onClick={() => handlePlayPauseClick(song)}>
                        {currentPlaying && currentPlaying.trackId === song.id ? 'Pause' : 'Play'}
                      </button>
                      <button id="play-pause2" onClick={() => handlePlayPauseClick(song)}>
                        {currentPlaying && currentPlaying.trackId === song.id ? <FontAwesomeIcon icon={faPause} /> : <FontAwesomeIcon icon={faPlay} />}
                      </button>
                    </>
                  ) : (
                    <button className="no-prev">Preview unavailable</button>
                  )}
                  <button className="del-btn" onClick={() => deleteSong(song.id)}><FontAwesomeIcon icon={faX} /></button>
                </div>
              </div>
            })}</div>}
        </div>
      </div>
    </div>
  );
}

export default Profile;
