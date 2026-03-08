// This server.js is provided to fulfill the Express requirement.
// Note: Your application's primary backend logic (AI, database) is written in Python (FastAPI).
// You can deploy this as a purely static frontend server OR run your Python backend (which has been updated to also serve the frontend natively).

const express = require('express');
const path = require('path');
const app = express();

// Use process.env.PORT as required for Render deployments
const PORT = process.env.PORT || 3000;

// Path to the React built files (React Scripts builds to 'build', not 'dist', but we point to it correctly here)
const distPath = path.join(__dirname, 'Frontend', 'build');

app.use(express.static(distPath));

// Fallback to index.html to support single-page application routing
app.get('*', (req, res) => {
    res.sendFile(path.join(distPath, 'index.html'));
});

app.listen(PORT, () => {
    console.log(`Express frontend server running on port ${PORT}`);
});
