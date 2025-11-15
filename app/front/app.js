const API_BASE = "http://127.0.0.1:6767";

async function apiGet(path) {
  const res = await fetch(API_BASE + path, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });
  return res.json();
}

async function apiPost(path, data) {
  const res = await fetch(API_BASE + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return res.json();
}

async function testConnection() {
  try {
    console.log("Testing backend connectivity...");
    const result = await apiGet("/ping");
    console.log("Backend ping result:", result);
  } catch (err) {
    console.error("Backend connection failed:", err);
  }
}

const state = {
  selectedCase: null,
  transcript: [
    { speaker: "Prosecutor", text: "State your name for the record." },
    { speaker: "Witness", text: "My name is Jordan Ellis." },
    { speaker: "Prosecutor", text: "Describe the night of May 4th." },
    { speaker: "Witness", text: "I was behind the bar when the argument started." },
    { speaker: "Prosecutor", text: "Did you see the defendant pull out a weapon?" },
    { speaker: "Witness", text: "I saw the crowd back away before the glass broke." },
    { speaker: "Prosecutor", text: "What happened after the defendant left?" },
    { speaker: "Witness", text: "The manager counted the register and it was short." },
    { speaker: "Prosecutor", text: "Was anyone injured?" },
    { speaker: "Witness", text: "There were a few scratches, but no serious injury." },
  ],
  currentLineIndex: 0,
  isPlaying: false,
  activeCaseIndex: null,
  activeCase: null,
  playerSide: null,
};

const updateHeader = (title) => {
  const headerEl = document.getElementById("app-header-title");
  if (headerEl) {
    headerEl.innerText = title;
  }
};

const showScreen = (id) => {
  document.querySelectorAll(".screen").forEach((screen) => screen.classList.add("hidden"));
  document.getElementById(id)?.classList.remove("hidden");
  if (id === "case-selection") {
    updateHeader("Courtroom Simulator");
  } else if (id === "case-summary") {
    updateHeader(state.selectedCase?.title ?? "Case Overview");
  } else if (id === "courtroom") {
    updateHeader(`${state.selectedCase?.title ?? "Courtroom"} — Direct Examination`);
  } else if (id === "trial-summary") {
    updateHeader("Trial Summary");
  }
};

const continueButton = document.querySelector(".actions .btn.primary");
const caseCards = Array.from(document.querySelectorAll(".case-card"));
const selectButtons = Array.from(document.querySelectorAll(".select-btn"));
const transcriptContainer = document.querySelector(".transcript-lines");
const transcriptStatus = document.querySelector(".transcript-panel footer");
const pauseToggle = document.querySelector(".pause-toggle");
const rulingText = document.querySelector(".ruling-summary .text-xl");
const sustainedCountEl = document.querySelector(".sustained-count");
const overruledCountEl = document.querySelector(".overruled-count");
const objectionGrid = document.querySelector(".objection-grid");
const judgeModal = document.getElementById("judge-modal");
const rulingOutcomeEl = document.getElementById("ruling-outcome");
const rulingExplanationEl = document.getElementById("ruling-explanation");
const closeModalBtn = document.getElementById("close-modal-btn");
const finalGradeEl = document.getElementById("final-grade");
const gradeExplanationEl = document.getElementById("grade-explanation");
const totalObjectionsEl = document.getElementById("total-objections");
const summarySustainedEl = document.getElementById("summary-sustained");
const summaryOverruledEl = document.getElementById("summary-overruled");
const accuracyRateEl = document.getElementById("accuracy-rate");
const judgeNotesEl = document.getElementById("judge-notes");


let playbackTimer = null;
let isPlaying = false;
const rulingCounts = { sustained: 0, overruled: 0 };
const rulingNarratives = {
  Sustained: "Judge sustains the objection and the question is withdrawn.",
  Overruled: "Judge overrules the objection; questioning continues.",
};

const objectionList = [
  "Irrelevant evidence",
  "Evidence is unfairly prejudicial, confusing, or waste of time",
  "Compound question",
  "Improper character testimony",
  "Improper use of crimes, wrongs",
  "Crimes/wrongs admissible",
  "Proving character",
  "Character exception",
  "Lack of personal knowledge",
  "Speculation",
  "Argumentative question",
  "Narrative answer",
  "Leading question",
  "Non-responsive answer",
  "Beyond the scope",
  "Opinion",
  "Opinion Exception (Lay Witness)",
  "Hearsay",
  "Not hearsay (Admission Against Interest)",
  "Not hearsay (Opposing Party’s Statement)",
  "Exception: Present Sense Impression",
  "Exception: Excited Utterance",
  "Exception: State of Mind",
  "Lack of proper foundation",
  "Improper conclusion of law",
];

const setTranscriptStatus = (text) => {
  if (transcriptStatus) {
    transcriptStatus.textContent = text;
  }
};

const clearTranscriptLines = () => {
  if (!transcriptContainer) return;
  transcriptContainer.innerHTML = "";
};

const typingState = {
  msgEl: null,
  cursor: null,
  text: "",
  pos: 0,
  timer: null,
  callback: null,
};

const clearTypingTimer = () => {
  if (typingState.timer) {
    clearTimeout(typingState.timer);
    typingState.timer = null;
  }
};

const removeCurrentLineHighlight = () => {
  transcriptContainer?.querySelectorAll(".transcript-line").forEach((line) => {
    line.classList.remove("current-line");
  });
};

const finishTyping = () => {
  clearTypingTimer();
  typingState.cursor?.remove();
  typingState.cursor = null;
  typingState.callback?.();
  typingState.callback = null;
  typingState.msgEl?.classList.remove("typing");
};

const continueTyping = () => {
  if (!isPlaying) return;
  if (!typingState.msgEl || typingState.pos >= typingState.text.length) {
    finishTyping();
    return;
  }

  typingState.msgEl.textContent = typingState.text.slice(0, typingState.pos + 1);
  if (typingState.cursor) typingState.msgEl.appendChild(typingState.cursor);
  transcriptContainer.scrollTop = transcriptContainer.scrollHeight;
  typingState.pos += 1;

  typingState.timer = setTimeout(continueTyping, 25);
};

const typeLine = (msgEl, text, callback) => {
  clearTypingTimer();
  typingState.msgEl = msgEl;
  typingState.text = text;
  typingState.pos = 0;
  typingState.callback = callback;
  typingState.cursor?.remove();
  typingState.cursor = document.createElement("span");
  typingState.cursor.className = "cursor";
  msgEl.textContent = "";
  msgEl.classList.add("typing");
  msgEl.appendChild(typingState.cursor);
  continueTyping();
};

const addNextTranscriptLine = () => {
  if (!transcriptContainer) return;
  if (state.currentLineIndex >= state.transcript.length) {
    setTranscriptStatus("Direct examination complete");
    isPlaying = false;
    state.isPlaying = false;
    pauseToggle?.classList.add("disabled");
    document.getElementById("end-of-exam")?.classList.remove("hidden");
    return;
  }

  const line = state.transcript[state.currentLineIndex];
  const entry = document.createElement("div");
  entry.className = "transcript-line";
  entry.innerHTML = `
    <span class="speaker">${line.speaker}:</span>
    <span class="msg"></span>
  `;
  removeCurrentLineHighlight();
  entry.classList.add("current-line");
  transcriptContainer.appendChild(entry);
  setTimeout(() => entry.classList.add("visible"), 50);
  const msgEl = entry.querySelector(".msg");
  typeLine(msgEl, line.text, () => {
    state.currentLineIndex += 1;
    scheduleNextLine();
  });
};

const scheduleNextLine = () => {
  clearTimeout(playbackTimer);
  if (!isPlaying) return;

  playbackTimer = setTimeout(() => {
    addNextTranscriptLine();
  }, 2500 + Math.random() * 500);
};

const startPlayback = () => {
  if (isPlaying) return;
  isPlaying = true;
  state.isPlaying = true;
  pauseToggle?.classList.remove("disabled");
  setTranscriptStatus("Playing – direct examination in progress");
  if (typingState.msgEl && typingState.pos < typingState.text.length) {
    continueTyping();
    return;
  }
  addNextTranscriptLine();
};

const pausePlayback = () => {
  if (!isPlaying) return;
  isPlaying = false;
  state.isPlaying = false;
  clearTimeout(playbackTimer);
  clearTypingTimer();
  setTranscriptStatus("Paused for objection");
};

const handleObjection = (type) => {
  pausePlayback();
  if (pauseToggle) {
    pauseToggle.textContent = "Resume";
  }
  const outcome = Math.random() < 0.5 ? "Sustained" : "Overruled";
  rulingCounts[outcome === "Sustained" ? "sustained" : "overruled"] += 1;
  if (rulingText) rulingText.textContent = outcome;
  if (sustainedCountEl) sustainedCountEl.textContent = `Sustained: ${rulingCounts.sustained}`;
  if (overruledCountEl) overruledCountEl.textContent = `Overruled: ${rulingCounts.overruled}`;
  setTranscriptStatus(`Paused for objection – ${outcome}`);
  openJudgeModal(outcome, rulingNarratives[outcome]);
};

const populateCaseSummaryFromBackend = () => {
  if (!state.activeCase) return;
  const caseInfo = state.activeCase.case_information || {};
  document.getElementById("case-title").textContent = caseInfo.case_title || "Untitled Case";
  document.getElementById("case-charges").textContent = (caseInfo.charges || []).join(", ");
  document.getElementById("case-description").textContent = caseInfo.description || "";
  document.getElementById("prosecution-narrative").textContent =
    caseInfo.prosecution_narrative || "";
  document.getElementById("defense-position").textContent = caseInfo.defense_position || "";
};

const renderObjectionButtons = () => {
  if (!objectionGrid) return;
  const filtered = objectionList.filter(
    (name) =>
      !name.toLowerCase().includes("exception") &&
      !name.toLowerCase().includes("not hearsay") &&
      !name.toLowerCase().includes("hearsay within hearsay")
  );
  objectionGrid.innerHTML = filtered
    .map(
      (name) => `
        <button class="btn secondary" type="button">${name}</button>
      `
    )
    .join("");
};

const initializeObjections = () => {
  renderObjectionButtons();
  const buttons = objectionGrid?.querySelectorAll("button");
  buttons?.forEach((button) => {
    button.addEventListener("click", () => handleObjection(button.textContent.trim()));
  });
};

const openJudgeModal = (outcome, explanation) => {
  if (!judgeModal) return;
  rulingOutcomeEl && (rulingOutcomeEl.textContent = outcome);
  rulingExplanationEl && (rulingExplanationEl.textContent = explanation ?? "");
  judgeModal.classList.remove("hidden");
};

const closeJudgeModal = () => {
  if (!judgeModal) return;
  judgeModal.classList.add("hidden");
  if (pauseToggle) {
    pauseToggle.textContent = "Pause";
  }
  startPlayback();
};

const computeGrade = (score) => {
  if (score >= 90) return "A";
  if (score >= 80) return "B";
  if (score >= 70) return "C";
  if (score >= 60) return "D";
  return "F";
};

const determineGradeExplanation = (score) => {
  if (score >= 90) return "Excellent objection timing and accuracy.";
  if (score >= 80) return "Good judgement, but overruled objections were too frequent.";
  if (score >= 70) return "Careful work, yet there is room to sharpen the rules of evidence.";
  return "Needs better application of the rules of evidence.";
};

const determineJudgeNotes = (accuracy, sustained, overruled) => {
  if (accuracy >= 0.8) return "Impressive command of the rules of evidence.";
  if (sustained === overruled) return "Mixed performance; room to improve precision.";
  if (overruled > sustained) return "Counsel must refine legal grounds for objections.";
  return "Keep the courtroom pressure steady.";
};

const showTrialSummary = () => {
  document.getElementById("end-of-exam")?.classList.add("hidden");
  const sustained = rulingCounts.sustained;
  const overruled = rulingCounts.overruled;
  const total = sustained + overruled;
  const accuracy = total ? sustained / total : 1;
  const accuracyScore =
    accuracy >= 0.8 ? 50 : accuracy >= 0.65 ? 40 : accuracy >= 0.5 ? 30 : 15;
  const volumeScore =
    total >= 8 ? 20 : total >= 5 ? 15 : total >= 3 ? 10 : 5;
  const dominanceScore =
    sustained >= overruled * 1.5 ? 30 : sustained >= overruled ? 20 : 10;

  const finalScore = accuracyScore + volumeScore + dominanceScore;
  const grade = computeGrade(finalScore);
  const gradeExplanation = determineGradeExplanation(finalScore);
  const judgeNote = determineJudgeNotes(accuracy, sustained, overruled);

  if (finalGradeEl) finalGradeEl.textContent = grade;
  if (gradeExplanationEl) gradeExplanationEl.textContent = gradeExplanation;
  if (totalObjectionsEl) totalObjectionsEl.textContent = total.toString();
  if (summarySustainedEl) summarySustainedEl.textContent = sustained.toString();
  if (summaryOverruledEl) summaryOverruledEl.textContent = overruled.toString();
  if (accuracyRateEl) accuracyRateEl.textContent = (accuracy * 100).toFixed(0);
  if (judgeNotesEl) judgeNotesEl.textContent = judgeNote;

  showScreen("trial-summary");
  const summary = document.getElementById("trial-summary");
  summary?.classList.add("fade-in");
};

const pickSide = async (side) => {
  if (state.activeCaseIndex === null) return;
  try {
    const updated = await apiPost("/pick-side", {
      activeCase: state.activeCaseIndex,
      side,
    });
    state.activeCase = updated.case;
    state.playerSide = side;
    state.selectedCase = state.activeCase;
    populateCaseSummaryFromBackend();
    showScreen("case-summary");
  } catch (err) {
    console.error("Failed to pick side", err);
  }
};

const resetTranscript = () => {
  clearTranscriptLines();
  state.currentLineIndex = 0;
  clearTypingTimer();
  typingState.msgEl?.classList.remove("typing");
  typingState.msgEl = null;
  typingState.text = "";
  typingState.pos = 0;
  typingState.callback = null;
  typingState.cursor?.remove();
  typingState.cursor = null;
  document.getElementById("end-of-exam")?.classList.add("hidden");
};

const setSelectedCard = (card) => {
  caseCards.forEach((entry) => entry.classList.remove("selected"));
  card.classList.add("selected");
  if (continueButton) {
    continueButton.disabled = false;
    continueButton.classList.add("is-ready");
  }
};

const createCaseAndSelect = async () => {
  const created = await apiGet("/create_case");
  state.activeCaseIndex = created.caseNum;
  state.activeCase = created.case;
  state.selectedCase = state.activeCase;
  const selected = await apiPost("/select_case", {
    activeCase: state.activeCaseIndex,
  });
  state.activeCase = selected.case;
  state.selectedCase = state.activeCase;
};

const handleCaseCardClick = async (card) => {
  setSelectedCard(card);
  try {
    await createCaseAndSelect();
    showScreen("side-selection");
  } catch (err) {
    console.error("Case selection failed", err);
  }
};

caseCards.forEach((card) => {
  card.addEventListener("click", () => handleCaseCardClick(card));
});

selectButtons.forEach((button) => {
  button.addEventListener("click", (event) => {
    event.stopPropagation();
    const card = button.closest(".case-card");
    if (card) handleCaseCardClick(card);
  });
});

continueButton?.addEventListener("click", () => {
  if (!state.selectedCase) return;
  resetTranscript();
  showScreen("courtroom");
  startPlayback();
});

pauseToggle?.addEventListener("click", () => {
  if (isPlaying) {
    pausePlayback();
    pauseToggle.textContent = "Resume";
  } else {
    pauseToggle.textContent = "Pause";
    startPlayback();
  }
});

closeModalBtn?.addEventListener("click", closeJudgeModal);

initializeObjections();

document.getElementById("back-to-selection")?.addEventListener("click", () => {
  showScreen("case-selection");
});

document.getElementById("start-exam")?.addEventListener("click", () => {
  resetTranscript();
  showScreen("courtroom");
  startPlayback();
});

document.getElementById("return-selection")?.addEventListener("click", () => {
  showScreen("case-selection");
});

document.getElementById("continue-to-summary")?.addEventListener("click", () => {
  showTrialSummary();
});

document.getElementById("choose-prosecution")?.addEventListener("click", () => {
  pickSide("prosecution");
});

document.getElementById("choose-defense")?.addEventListener("click", () => {
  pickSide("defense");
});

const enableHeaderShrink = () => {
  const header = document.getElementById("app-header");
  if (!header) return;
  window.addEventListener("scroll", () => {
    if (window.scrollY > 18) {
      header.classList.add("shrink");
    } else {
      header.classList.remove("shrink");
    }
  });
};

enableHeaderShrink();

testConnection();

export { showScreen, state };
