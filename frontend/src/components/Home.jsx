import React from 'react';

function Home() {

  return (
    <div className="app">
      <div className="app-login">
        <h1>Elevate: Your Personalized Playlist Builder!</h1>
        <p>Discover a new way to enjoy music that perfectly 
          matches your mood and activity. Just log in with your 
          Spotify account, select an activity—whether it’s working 
          out, relaxing, or even cooking—and let us create a 
          custom playlist tailored just for you. We’ll analyze 
          your unique listening history and the most popular 
          playlists to make sure every track hits the right vibe. 
          Get ready to elevate your music experience!</p>
        <a href="https://18.218.68.142:5001/login"><button>Connect to Spotify</button></a>      
      </div>
    </div>
  );
}

export default Home;
