chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "checkUrlSecurity") {
    fetch('http://127.0.0.1:5000/predict', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: request.url })
    })
    .then(res => res.json())
    .then(data => sendResponse({ success: true, data: data }))
    .catch(err => sendResponse({ success: false, error: err.toString() }));
    return true; 
  }
});