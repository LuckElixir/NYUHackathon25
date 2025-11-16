// ----------------------------------------------
// GLOBAL STATE
// ----------------------------------------------
const state = {
  caseIndex: null,
  caseData: null,
  playerSide: null,
  isPlaying: false,
  autoLoopTimer: null,
};


// ----------------------------------------------
// HELPERS
// ----------------------------------------------
function showScreen(id) {
  document.querySelectorAll(".screen").forEach(s => s.classList.add("hidden"));
  document.getElementById(id).classList.remove("hidden");
}

function autoScrollTranscript() {
  const box = document.getElementById("transcript-lines");
  box.scrollTop = box.scrollHeight;
}

function setTranscriptStatus(text) {
  document.getElementById("transcript-status").textContent = text;
}

function disableAutoLoop() {
  state.isPlaying = false;
  clearTimeout(state.autoLoopTimer);
  state.autoLoopTimer = null;
}

function buildTimelinePrompt() {
  const timeline = state.caseData?.timeline || [];
  if (!timeline.length) return "";

  const recent = timeline
    .slice(-10)
    .map((ev) => `[${ev.type}] ${ev.speaker}: ${ev.content}`)
    .join("\n");

  return `You are continuing a courtroom transcript. Recent context:\n${recent}\nContinue with the next natural event.`;
}


// ----------------------------------------------
// API CALL HELPERS
// ----------------------------------------------
async function createCase() {
  const res = await fetch("/create_case");
  const data = await res.json();
  if (data.response !== "success") return alert("Failed to create case.");

  state.caseIndex = data.caseNum;
  state.caseData = data.case;

  return data.case;
}

async function pickSide(side) {
  const res = await fetch("/pick-side", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      activeCase: state.caseIndex,
      side
    })
  });

  const data = await res.json();
  if (data.response !== "success") return alert("Side pick failed.");

  state.caseData = data.case;
}

async function generateAIEvent() {
  const prompt = buildTimelinePrompt();
  const res = await fetch("/ai-event", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      case_index: state.caseIndex,
      speaker:
        state.playerSide === "prosecution"
          ? state.caseData.prosecution_name
          : state.caseData.defense_name,
      prompt
    })
  });

  const data = await res.json();
  if (data.response !== "success") {
    console.log("AI event failed:", data);
    disableAutoLoop();
    return;
  }

  state.caseData = data.case;
  renderTimeline();
}

async function sendObjection(type) {
  const res = await fetch("/object", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      case_index: state.caseIndex,
      speaker: state.playerSide === "prosecution"
        ? state.caseData.prosecution_name
        : state.caseData.defense_name,
      objection_type: type,
      content: "Objection!"
    })
  });

  const data = await res.json();
  if (data.response !== "success") {
    alert("Objection failed.");
    return;
  }

state.caseData = data.case;
renderTimeline();

// --- Update the sidebar ruling summary ---
document.getElementById("last-ruling-text").textContent = data.ruling.decision;

// Show Judge Ruling Modal
const outcomeEl = document.getElementById("ruling-outcome");
const explanationEl = document.getElementById("ruling-explanation");

outcomeEl.textContent = data.ruling.decision;
explanationEl.textContent = data.ruling.content;

// Clear old classes
outcomeEl.classList.remove("judge-sustained", "judge-overruled");

// Apply color
const decisionLower = data.ruling.decision.toLowerCase();
if (decisionLower.includes("overruled")) {
  outcomeEl.classList.add("judge-overruled");
} else if (decisionLower.includes("sustain")) {
  outcomeEl.classList.add("judge-sustained");
}

document.getElementById("judge-modal").classList.remove("hidden");

function buildTimelinePrompt() {
  const timeline = state.caseData?.timeline || [];
  if (!timeline.length) return "";

  const recent = timeline.slice(-10)
    .map(ev => `[${ev.type}] ${ev.speaker}: ${ev.content}`)
    .join("\n");

  return `You are continuing a courtroom transcript. Recent context:\n${recent}\nContinue with the next natural event.`;
}

document.getElementById("judge-modal").classList.remove("hidden");
}


// ----------------------------------------------
// RENDER FUNCTIONS
// ----------------------------------------------
function renderCaseSummary(c) {
  document.getElementById("case-title").textContent = c.case_title;
  document.getElementById("case-description").textContent = c.description;
  document.getElementById("judge-name").textContent = c.judge;
  document.getElementById("prosecution-name").textContent = c.prosecution_name;
  document.getElementById("defense-name").textContent = c.defense_name;

  const wl = document.getElementById("witness-list");
  wl.innerHTML = "";
  Object.keys(c.witnesses).forEach(name => {
    const li = document.createElement("li");
    li.textContent = name;
    wl.appendChild(li);
  });
}

function renderTimeline() {
  const container = document.getElementById("transcript-lines");
  container.innerHTML = "";

  const timeline = state.caseData.timeline;

  for (const ev of timeline) {
    const wrapper = document.createElement("div");
    wrapper.className = "transcript-line";

let tagClass = "";
let lineClass = "";

if (ev.type === "OBJECTION") {
  tagClass = "event-objection";
  lineClass = "timeline-objection";
}
else if (ev.type === "RULING") {
  // Determine sustained / overruled from content text
  const isOverruled = ev.content.toLowerCase().includes("overruled");
  const isSustained = ev.content.toLowerCase().includes("sustain");

  if (isOverruled) {
    tagClass = "event-ruling-overruled";
    lineClass = "timeline-ruling-overruled";
  } else if (isSustained) {
    tagClass = "event-ruling-sustained";
    lineClass = "timeline-ruling-sustained";
  }
}

wrapper.className = `transcript-line ${lineClass}`;

wrapper.innerHTML = `
  <div class="meta">
    <span class="event-tag ${tagClass}">[${ev.type}]</span>
    ${ev.speaker}:
  </div>
  <div class="content">${ev.content}</div>
`;

    container.appendChild(wrapper);

    // 🔥 Required for visibility (CSS fade-in animation)
    requestAnimationFrame(() => {
      wrapper.classList.add("visible");
    });
  }

  autoScrollTranscript();
}


// ----------------------------------------------
// AUTO-LOOP FOR /ai-event
// ----------------------------------------------
function startAutoLoop() {
  if (state.isPlaying) return;

  state.isPlaying = true;
  setTranscriptStatus("AI Generating...");
  nextLoop();
}

function nextLoop() {
  if (!state.isPlaying) return;

  state.autoLoopTimer = setTimeout(async () => {
    await generateAIEvent();
    nextLoop();
  }, 1800);
}


// ----------------------------------------------
// UI EVENT BINDINGS
// ----------------------------------------------
document.getElementById("btn-generate-case").onclick = async () => {
  const c = await createCase();
  renderCaseSummary(c);
  showScreen("case-summary");
};

// Pick side
document.getElementById("btn-side-prosecution").onclick = async () => {
  state.playerSide = "prosecution";
  document.getElementById("selected-side-label").textContent = "You selected: Prosecution";
  await pickSide("prosecution");
  document.getElementById("start-exam").disabled = false;
};

document.getElementById("btn-side-defense").onclick = async () => {
  state.playerSide = "defense";
  document.getElementById("selected-side-label").textContent = "You selected: Defense";
  await pickSide("defense");
  document.getElementById("start-exam").disabled = false;
};

// Back button
document.getElementById("back-to-generation").onclick = () => {
  showScreen("case-generation");
};

// Start exam
document.getElementById("start-exam").onclick = () => {
  showScreen("courtroom");

  document.getElementById("courtroom-title").textContent =
    `Live Examination — You are the ${state.playerSide}`;

  renderTimeline();
  startAutoLoop();
};

// Pause / Resume
document.getElementById("pause-btn").onclick = () => {
  if (state.isPlaying) {
    disableAutoLoop();
    setTranscriptStatus("Paused");
    document.getElementById("pause-btn").textContent = "Resume";
  } else {
    startAutoLoop();
    document.getElementById("pause-btn").textContent = "Pause";
  }
};

// Objection buttons
const objections = [
  "Irrelevant", "Speculation", "Leading", "Hearsay",
  "Compound", "Argumentative", "Lack of Foundation"
];

const objGrid = document.getElementById("objection-grid");
objGrid.innerHTML = objections.map(o =>
  `<button class="btn secondary objection-btn">${o}</button>`
).join("");

objGrid.addEventListener("click", (e) => {
  if (e.target.classList.contains("objection-btn")) {
    disableAutoLoop();
    sendObjection(e.target.textContent);
  }
});

// Close Judge modal
document.getElementById("close-modal-btn").onclick = () => {
  document.getElementById("judge-modal").classList.add("hidden");
  startAutoLoop();
};
