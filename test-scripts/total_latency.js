const axios = require('axios');

const MAILHOG_API = 'http://localhost:8025/api/v2/messages';
const PAGE_LIMIT = 50;

function parseIsoTimeToMillis(isoTime) {
  try {
    const clean = isoTime.trim().slice(0, 23);
    const millis = Date.parse(clean + 'Z');
    return millis;
  } catch (e) {
    return null;
  }
}

async function fetchAllMessages() {
  let messages = [];
  let start = 0;
  let total = Infinity;

  while (start < total) {
    try {
      const res = await axios.get(`${MAILHOG_API}?start=${start}&limit=${PAGE_LIMIT}`);
      const pageMessages = res.data.items || [];
      total = res.data.total || 0;

      messages.push(...pageMessages);
      start += PAGE_LIMIT;
    } catch (err) {
      console.error(`Failed to fetch messages from offset ${start}:`, err.message);
      break;
    }
  }

  return messages;
}

async function calculateLatency() {
  const messages = await fetchAllMessages();
  if (!messages || messages.length === 0) {
    console.log("No messages found in MailHog.");
    return;
  }

  let totalLatencyMs = 0;
  let count = 0;

  for (const msg of messages) {
    const createdStr = msg.Created;
    const bodyStr = msg.Content.Body.trim();

    // Split into lines and find the one that is just the timestamp
    const lines = bodyStr.split(/\r\n|\r|\n/);
    const tsLine = lines.find(line =>
      /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z$/.test(line)
    );

    // If no valid timestamp line, skip
    if (!tsLine) {
      continue;
    }

    // tsLine now holds "2025-05-04T21:19:20.549324951000Z"
    const timestamp = tsLine;
    // console.log("Extracted timestamp:", timestamp);

    const createdTime = parseIsoTimeToMillis(createdStr);
    const sentTime = parseIsoTimeToMillis(timestamp);

    if (!createdTime || !sentTime) {
      continue;
    }

    const latency = createdTime - sentTime;

    if (latency < 0 || latency > 60000) {
      continue;
    }

    totalLatencyMs += latency;
    count++;
  }

  if (count === 0) {
    console.log("No valid messages processed.");
  } else {
    const avgLatency = totalLatencyMs / count;
    console.log(`Processed ${count} messages`);
    console.log(`Average Latency: ${avgLatency.toFixed(2)} ms`);
  }
}

calculateLatency();