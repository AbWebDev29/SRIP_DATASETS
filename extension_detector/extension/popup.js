/**
 * Phishing Shield Popup Script v2
 * Manual click-on-demand analysis flow
 * NO persistent background listeners - purely popup-scoped execution
 */

// Global state for current tab
let currentTabUrl = null;

/**
 * Truncate long URLs elegantly for display
 */
function truncateUrl(url, maxLength = 45) {
  if (!url) return "No URL";
  if (url.length <= maxLength) return url;
  return url.substring(0, maxLength) + "...";
}

/**
 * Update result display with status and styling
 */
function updateResult(message, className = "") {
  const resultDiv = document.getElementById('result');
  resultDiv.innerText = message;
  resultDiv.className = className;
}

/**
 * Call Flask backend for phishing prediction
 */
async function analyzeSingleUrl(url) {
  try {
    const response = await fetch('http://127.0.0.1:5000/predict', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ url: url })
    });

    if (!response.ok) {
      const errorData = await response.json();
      return {
        error: true,
        message: `Server error: ${errorData.error || 'Unknown error'}`
      };
    }

    const data = await response.json();
    return {
      error: false,
      is_phishing: data.is_phishing,
      probability: data.probability,
      status: data.status
    };
  } catch (error) {
    return {
      error: true,
      message: `Connection failed: ${error.message}`
    };
  }
}

/**
 * Format and display prediction result
 */
function displayPredictionResult(prediction) {
  if (prediction.error) {
    updateResult(
      `⚠️ Analysis Error\n${prediction.message}`,
      'error'
    );
    return;
  }

  const confidencePercent = (prediction.probability * 100).toFixed(1);
  
  if (prediction.is_phishing === 1) {
    updateResult(
      `🚨 PHISHING DETECTED\nConfidence: ${confidencePercent}%`,
      'unsafe'
    );
  } else {
    updateResult(
      `✅ SAFE URL\nRisk Level: ${confidencePercent}%`,
      'safe'
    );
  }
}

/**
 * Main entry point - runs once on popup open
 */
document.addEventListener('DOMContentLoaded', async () => {
  const urlDisplay = document.getElementById('urlDisplay');
  const scanBtn = document.getElementById('scanBtn');
  const resultDiv = document.getElementById('result');

  try {
    // Fetch the active tab's URL ONCE
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    
    if (!tabs || tabs.length === 0) {
      urlDisplay.innerText = "Error: Cannot access tab information";
      scanBtn.disabled = true;
      return;
    }

    const tab = tabs[0];
    
    if (!tab.url) {
      urlDisplay.innerText = "Error: Tab has no URL";
      scanBtn.disabled = true;
      return;
    }

    currentTabUrl = tab.url;
    
    // Display the URL elegantly
    urlDisplay.innerText = truncateUrl(currentTabUrl);

    // Handle internal browser pages
    if (
      currentTabUrl.startsWith('chrome://') ||
      currentTabUrl.startsWith('about:') ||
      currentTabUrl.startsWith('chrome-extension://')
    ) {
      updateResult('✅ Browser System Page\nNo analysis needed', 'safe');
      scanBtn.disabled = true;
      return;
    }

    // Set initial state
    updateResult('Ready for analysis', '');

  } catch (error) {
    console.error('Error loading tab info:', error);
    urlDisplay.innerText = "Error: Failed to load tab";
    updateResult(`Error: ${error.message}`, 'error');
    scanBtn.disabled = true;
  }

  // Attach click listener to scan button
  scanBtn.addEventListener('click', async () => {
    if (!currentTabUrl) {
      updateResult('Error: No URL to analyze', 'error');
      return;
    }

    // Disable button and show loading state
    scanBtn.disabled = true;
    updateResult('Analyzing URL...', 'loading');

    // Perform analysis
    const prediction = await analyzeSingleUrl(currentTabUrl);
    
    // Display result
    displayPredictionResult(prediction);

    // Re-enable button
    scanBtn.disabled = false;
  });
});
