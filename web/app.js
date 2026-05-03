const DATA_ROOT = "../data/processed";
const DEFAULT_STATION_AMBIENCE = "./assets/station-ambience.mp3";
const TRAIN_SOUND_POOL = [
  "./assets/train-passing-level-crossing.mp3",
  "./assets/train-rural-horn-wind.mp3",
  "./assets/train-vestibule-interior.mp3",
];
const PA_LOOKAHEAD_MINUTES = 15;
const INDIA_BOUNDS = {
  minLat: 6.2,
  maxLat: 37.8,
  minLon: 68.0,
  maxLon: 97.6,
};

const INDIA_OUTLINE = [
  [68.2, 23.7],
  [69.4, 22.1],
  [70.1, 20.5],
  [72.6, 18.8],
  [72.9, 15.1],
  [74.0, 12.9],
  [75.8, 8.2],
  [77.4, 8.1],
  [79.7, 10.4],
  [80.3, 13.1],
  [80.1, 15.6],
  [82.0, 17.8],
  [84.7, 19.4],
  [86.8, 21.1],
  [88.0, 21.6],
  [88.3, 22.7],
  [89.7, 22.0],
  [91.6, 23.5],
  [93.1, 24.1],
  [94.7, 25.6],
  [95.2, 27.4],
  [96.7, 28.3],
  [95.5, 29.2],
  [94.1, 28.6],
  [92.6, 27.6],
  [91.3, 26.9],
  [89.8, 26.8],
  [88.1, 27.8],
  [88.0, 30.3],
  [85.8, 29.4],
  [83.9, 27.4],
  [81.8, 30.5],
  [79.2, 31.9],
  [76.8, 34.5],
  [74.9, 34.8],
  [73.8, 32.6],
  [71.0, 28.0],
  [68.2, 23.7],
];

const state = {
  mode: "train",
  stations: {},
  trains: {},
  selectedTrainNo: null,
  selectedStationCode: null,
  trainEvents: [],
  stationEvents: [],
  startedAt: 0,
  simStartMinutes: 0,
  currentMinutes: 0,
  previousMinutes: 0,
  speed: 1,
  playing: false,
  soundEnabled: false,
  soundStatus: "silent",
  audio: null,
  stationAmbienceAudio: null,
  stationAmbienceUrl: null,
  trainTravelAudio: null,
  currentTrainSound: null,
  trainSoundQueue: [],
  autoPaEnabled: true,
  autoPaLastAt: 0,
  autoPaIndex: 0,
  activeAnnouncementKey: null,
  activeStationEvent: null,
  announcedEvents: new Set(),
  announcementQueue: [],
  announcementBusy: false,
  people: [],
  vendors: [],
  lastFrameAt: performance.now(),
};

const els = {
  canvas: document.querySelector("#scene"),
  modeLabel: document.querySelector("#modeLabel"),
  primaryTitle: document.querySelector("#primaryTitle"),
  primarySubtitle: document.querySelector("#primarySubtitle"),
  clockLabel: document.querySelector("#clockLabel"),
  clockStatus: document.querySelector("#clockStatus"),
  trainModeButton: document.querySelector("#trainModeButton"),
  stationModeButton: document.querySelector("#stationModeButton"),
  trainSearch: document.querySelector("#trainSearch"),
  trainOptions: document.querySelector("#trainOptions"),
  stationSearch: document.querySelector("#stationSearch"),
  stationOptions: document.querySelector("#stationOptions"),
  playButton: document.querySelector("#playButton"),
  resetButton: document.querySelector("#resetButton"),
  soundButton: document.querySelector("#soundButton"),
  testAnnouncementButton: document.querySelector("#testAnnouncementButton"),
  autoPaButton: document.querySelector("#autoPaButton"),
  ambienceFile: document.querySelector("#ambienceFile"),
  speedSlider: document.querySelector("#speedSlider"),
  speedLabel: document.querySelector("#speedLabel"),
  speedPresets: Array.from(document.querySelectorAll(".speedPreset")),
  timelineScrubber: document.querySelector("#timelineScrubber"),
  timelineRangeLabel: document.querySelector("#timelineRangeLabel"),
  prevEventButton: document.querySelector("#prevEventButton"),
  nextEventButton: document.querySelector("#nextEventButton"),
  preAnnounceButton: document.querySelector("#preAnnounceButton"),
  detailTitle: document.querySelector("#detailTitle"),
  detailBody: document.querySelector("#detailBody"),
};

const ctx = els.canvas.getContext("2d");

function minutesFromEvent(event) {
  const [hours, minutes] = event.time.split(":").map(Number);
  return event.dayOffset * 1440 + hours * 60 + minutes;
}

function formatClock(value) {
  const totalSeconds =
    ((Math.floor(value * 60) % 86400) + 86400) % 86400;
  const hours = String(Math.floor(totalSeconds / 3600)).padStart(2, "0");
  const minutes = String(Math.floor((totalSeconds % 3600) / 60)).padStart(2, "0");
  const seconds = String(totalSeconds % 60).padStart(2, "0");
  return `${hours}:${minutes}:${seconds}`;
}

function formatMinutes(value) {
  const wrapped = ((Math.floor(value) % 1440) + 1440) % 1440;
  const hours = String(Math.floor(wrapped / 60)).padStart(2, "0");
  const minutes = String(wrapped % 60).padStart(2, "0");
  return `${hours}:${minutes}`;
}

function activeMapBounds() {
  if (state.mode !== "train") {
    return INDIA_BOUNDS;
  }
  const train = state.trains[state.selectedTrainNo];
  const points = train?.mappedRoute
    .map((code) => state.stations[code])
    .filter((station) => station?.lat != null && station?.lon != null);
  if (!points || points.length < 2) {
    return INDIA_BOUNDS;
  }

  let minLat = Math.min(...points.map((point) => point.lat));
  let maxLat = Math.max(...points.map((point) => point.lat));
  let minLon = Math.min(...points.map((point) => point.lon));
  let maxLon = Math.max(...points.map((point) => point.lon));
  const latPadding = Math.max(0.35, (maxLat - minLat) * 0.28);
  const lonPadding = Math.max(0.35, (maxLon - minLon) * 0.28);
  minLat = Math.max(INDIA_BOUNDS.minLat, minLat - latPadding);
  maxLat = Math.min(INDIA_BOUNDS.maxLat, maxLat + latPadding);
  minLon = Math.max(INDIA_BOUNDS.minLon, minLon - lonPadding);
  maxLon = Math.min(INDIA_BOUNDS.maxLon, maxLon + lonPadding);

  return {
    minLat,
    maxLat: Math.max(maxLat, minLat + 0.5),
    minLon,
    maxLon: Math.max(maxLon, minLon + 0.5),
  };
}

function projectPoint(lat, lon, bounds = activeMapBounds()) {
  return {
    x: ((lon - bounds.minLon) / (bounds.maxLon - bounds.minLon)) * els.canvas.width,
    y:
      (1 - (lat - bounds.minLat) / (bounds.maxLat - bounds.minLat)) *
      els.canvas.height,
  };
}

function activeTimelineEvents() {
  return state.mode === "station" && state.stationEvents.length > 0
    ? state.stationEvents
    : state.trainEvents;
}

function timelineBounds() {
  const eventMinutes = activeTimelineEvents().map(minutesFromEvent);
  if (eventMinutes.length === 0) {
    return { min: 0, max: 1440 };
  }
  return {
    min: Math.min(...eventMinutes),
    max: Math.max(...eventMinutes),
  };
}

function setClockMinutes(value, { clearPa = true } = {}) {
  state.previousMinutes = state.currentMinutes;
  state.currentMinutes = Number(value);
  if (clearPa) {
    state.announcedEvents.clear();
    state.activeAnnouncementKey = null;
    state.autoPaLastAt = 0;
  }
  renderDetails();
  syncTimelineControls();
}

function syncTimelineControls() {
  const bounds = timelineBounds();
  els.timelineScrubber.min = String(bounds.min);
  els.timelineScrubber.max = String(Math.max(bounds.min + 0.25, bounds.max));
  els.timelineScrubber.value = String(
    Math.max(bounds.min, Math.min(bounds.max, state.currentMinutes)),
  );
  els.timelineRangeLabel.textContent = `${formatClock(state.currentMinutes)} / ${formatMinutes(
    bounds.min,
  )}-${formatMinutes(bounds.max)}`;
}

function nearestEvent(direction) {
  const events = currentAnnouncementEvents();
  if (direction < 0) {
    return events
      .slice()
      .reverse()
      .find((event) => minutesFromEvent(event) < state.currentMinutes - 0.01);
  }
  return events.find((event) => minutesFromEvent(event) > state.currentMinutes + 0.01);
}

function jumpToEvent(direction) {
  const event = nearestEvent(direction);
  if (event) {
    setClockMinutes(minutesFromEvent(event));
  }
}

function jumpToPreAnnouncement() {
  const event =
    currentAnnouncementEvents().find(
      (candidate) => minutesFromEvent(candidate) >= state.currentMinutes,
    ) || currentAnnouncementEvents()[0];
  if (event) {
    setClockMinutes(Math.max(timelineBounds().min, minutesFromEvent(event) - 15));
  }
}

function stationPoint(code) {
  const station = state.stations[code];
  if (!station || station.lat == null || station.lon == null) {
    return null;
  }
  return {
    code,
    name: station.name,
    lat: station.lat,
    lon: station.lon,
    ...projectPoint(station.lat, station.lon),
  };
}

function resizeCanvas() {
  const rect = els.canvas.getBoundingClientRect();
  const scale = window.devicePixelRatio || 1;
  els.canvas.width = Math.max(640, Math.floor(rect.width * scale));
  els.canvas.height = Math.max(420, Math.floor(rect.height * scale));
}

function fitLabel(text, max = 28) {
  return text.length > max ? `${text.slice(0, max - 1)}...` : text;
}

async function loadInitialData() {
  const [stationsResponse, trainsResponse] = await Promise.all([
    fetch(`${DATA_ROOT}/stations.json`),
    fetch(`${DATA_ROOT}/train_summaries.json`),
  ]);
  const stationPayload = await stationsResponse.json();
  const trainPayload = await trainsResponse.json();
  state.stations = stationPayload.stations;
  state.trains = trainPayload.trains;

  populateOptions();
  await selectTrain("107");
  await selectStation("NDLS");
  setMode("train");
  resetClock();
}

function populateOptions() {
  const trainFragment = document.createDocumentFragment();
  Object.values(state.trains)
    .filter((train) => train.mappedRoute.length >= 2)
    .slice(0, 900)
    .forEach((train) => {
      const option = document.createElement("option");
      option.value = `${train.trainNo} - ${train.name}`;
      trainFragment.append(option);
    });
  els.trainOptions.replaceChildren(trainFragment);

  const stationFragment = document.createDocumentFragment();
  Object.values(state.stations)
    .filter((station) => station.lat != null && station.lon != null)
    .sort((a, b) => b.eventCount - a.eventCount)
    .slice(0, 1200)
    .forEach((station) => {
      const option = document.createElement("option");
      option.value = `${station.code} - ${station.name}`;
      stationFragment.append(option);
    });
  els.stationOptions.replaceChildren(stationFragment);
}

function parseLeadingCode(value) {
  return value.split(" - ")[0].trim().toUpperCase();
}

async function selectTrain(value) {
  const trainNo = parseLeadingCode(value);
  const train = state.trains[trainNo];
  if (!train) {
    return;
  }
  state.selectedTrainNo = trainNo;
  els.trainSearch.value = `${train.trainNo} - ${train.name}`;
  const response = await fetch(`${DATA_ROOT}/${train.eventsPath}`);
  const payload = await response.json();
  state.trainEvents = payload.events;
  resetClock();
  renderDetails();
  updateHeader();
}

async function selectStation(value) {
  const code = parseLeadingCode(value);
  const station = state.stations[code];
  if (!station) {
    return;
  }
  state.selectedStationCode = code;
  els.stationSearch.value = `${station.code} - ${station.name}`;
  if (station.eventsPath) {
    const response = await fetch(`${DATA_ROOT}/${station.eventsPath}`);
    const payload = await response.json();
    state.stationEvents = payload.events;
  } else {
    state.stationEvents = [];
  }
  state.announcedEvents.clear();
  state.autoPaIndex = 0;
  state.autoPaLastAt = 0;
  state.activeAnnouncementKey = null;
  state.activeStationEvent = null;
  resetCrowd();
  renderDetails();
  updateHeader();
}

function setMode(mode) {
  state.mode = mode;
  state.announcedEvents.clear();
  state.autoPaIndex = 0;
  state.autoPaLastAt = 0;
  state.activeAnnouncementKey = null;
  state.activeStationEvent = null;
  els.trainModeButton.classList.toggle("active", mode === "train");
  els.stationModeButton.classList.toggle("active", mode === "station");
  resetClock();
  resetCrowd();
  renderDetails();
  updateHeader();
}

function resetClock() {
  const first =
    state.mode === "station" && state.stationEvents.length > 0
      ? state.stationEvents[0]
      : state.trainEvents[0];
  state.simStartMinutes = first ? minutesFromEvent(first) : 0;
  state.currentMinutes = state.simStartMinutes;
  state.previousMinutes = state.currentMinutes;
  state.startedAt = performance.now();
  state.announcedEvents.clear();
  syncTimelineControls();
}

function updateHeader() {
  if (state.mode === "train") {
    const train = state.trains[state.selectedTrainNo];
    els.modeLabel.textContent = "Train View";
    els.primaryTitle.textContent = train
      ? `${train.trainNo} ${train.name}`
      : "Choose a train";
    els.primarySubtitle.textContent = train
      ? `${train.mappedRoute.length} mapped stops. Watch it move station to station across the railway map.`
      : "Search for a train to begin.";
    return;
  }

  const station = state.stations[state.selectedStationCode];
  els.modeLabel.textContent = "Station View";
  els.primaryTitle.textContent = station
    ? `${station.code} ${station.name}`
    : "Choose a station";
  els.primarySubtitle.textContent = station
    ? `${station.eventCount} scheduled train events. Vendors, passengers, and station ambience take focus here.`
    : "Search for a station to begin.";
}

function renderDetails() {
  if (state.mode === "train") {
    const train = state.trains[state.selectedTrainNo];
    els.detailTitle.textContent = "Train Timetable";
    if (!train) {
      els.detailBody.textContent = "No train selected.";
      return;
    }
    const list = document.createElement("ol");
    list.className = "route-list";
    train.route.slice(0, 24).forEach((code) => {
      const station = state.stations[code];
      const stationEvents = state.trainEvents.filter(
        (event) => event.stationCode === code && event.type !== "Transit",
      );
      const arrival = stationEvents.find((event) => event.type === "Arrival");
      const departure = stationEvents.find((event) => event.type === "Departure");
      const times = [
        arrival ? `Arr ${arrival.time.slice(0, 5)}` : null,
        departure ? `Dep ${departure.time.slice(0, 5)}` : null,
      ]
        .filter(Boolean)
        .join(" · ");
      const item = document.createElement("li");
      const active = stationEvents.some(
        (event) =>
          Math.abs(minutesFromEvent(event) - state.currentMinutes) <= 2,
      );
      item.classList.toggle("active", active);
      item.innerHTML = `<span class="code">${code}</span><span>${fitLabel(
        station?.name || "Unknown station",
      )}<br><span class="meta">${times || "No scheduled stop time"}${
        station?.lat == null ? " · No coordinates" : ""
      }</span></span>`;
      list.append(item);
    });
    els.detailBody.replaceChildren(list);
    return;
  }

  const station = state.stations[state.selectedStationCode];
  els.detailTitle.textContent = "Station";
  if (!station) {
    els.detailBody.textContent = "No station selected.";
    return;
  }
  const list = document.createElement("ul");
  list.className = "event-list";
  const matchingEvents = upcomingAnnouncementEvents(10);
  const rows = matchingEvents.length
    ? matchingEvents
    : [
        {
          time: "00:00:00",
          type: "Station",
          trainNo: station.code,
          trainName: `${station.eventCount} daily events in full timetable`,
        },
      ];
  rows.forEach((event) => {
    const item = document.createElement("li");
    const key = announcementKey(event, announcementScope());
    item.dataset.eventKey = key;
    item.classList.toggle("active", key === state.activeAnnouncementKey);
    item.innerHTML = `<span class="code">${event.time.slice(
      0,
      5,
    )}</span><span>${event.type} ${event.trainNo}<br><span class="meta">Platform ${platformForEvent(
      event,
    )} · ${fitLabel(
      event.trainName,
      32,
    )}</span></span>`;
    list.append(item);
  });
  els.detailBody.replaceChildren(list);
}

function platformForEvent(event) {
  const seed = `${event.trainNo}${event.stationCode || ""}`
    .split("")
    .reduce((total, char) => total + char.charCodeAt(0), 0);
  return String((seed % 8) + 1);
}

function spokenTrainNumber(trainNo) {
  return String(trainNo).split("").join(" ");
}

function spokenTime(event) {
  const [hourText, minuteText] = event.time.split(":");
  let hour = Number(hourText);
  const minute = Number(minuteText);
  const ampm = hour >= 12 ? "PM" : "AM";
  hour = hour % 12 || 12;
  return `${hour}:${String(minute).padStart(2, "0")} ${ampm}`;
}

function announcementTexts(event) {
  const platform = platformForEvent(event);
  const trainNo = spokenTrainNumber(event.trainNo);
  const time = spokenTime(event);
  const train = `train number ${trainNo}, ${event.trainName}`;
  const hindiTrain = `gaadi sankhya ${trainNo}, ${event.trainName}`;
  const origin = event.sourceStation || "its source station";
  const destination = event.destinationStation || "its destination";

  if (event.type === "Arrival") {
    return {
      english: [
        "May I have your attention please.",
        `${train}, from ${origin} to ${destination}, is arriving at platform number ${platform} at ${time}.`,
        "Passengers are requested to stand behind the yellow line.",
      ].join(" "),
      hindi: [
        "Yatrigan kripya dhyan dijiye.",
        `${origin} se chalkar ${destination} ko jaane wali ${hindiTrain}`,
        `platform sankhya ${platform} par ${time} baje aa rahi hai.`,
      ].join(" "),
    };
  }

  return {
    english: [
      "May I have your attention please.",
      `${train}, from ${origin} to ${destination}, will depart from platform number ${platform} at ${time}.`,
      "Passengers are requested to board the train and mind their belongings.",
    ].join(" "),
    hindi: [
      "Yatrigan kripya dhyan dijiye.",
      `${origin} se ${destination} ko jaane wali ${hindiTrain}`,
      `platform sankhya ${platform} se ${time} baje prasthan karegi.`,
    ].join(" "),
  };
}

function announcementKey(event, scope) {
  return [
    scope,
    event.trainNo,
    event.type,
    event.stationCode,
    event.time,
    event.dayOffset,
  ].join(":");
}

function announcementScope() {
  return state.mode === "station"
    ? `station:${state.selectedStationCode}`
    : `train:${state.selectedTrainNo}`;
}

function enqueueAnnouncement(event, scope) {
  if (!state.soundEnabled || event.type === "Transit") {
    return;
  }
  const key = announcementKey(event, scope);
  if (state.announcedEvents.has(key)) {
    return;
  }
  state.announcedEvents.add(key);
  state.announcementQueue.push({ event, scope, texts: announcementTexts(event) });
  state.announcementQueue = state.announcementQueue.slice(-4);
  processAnnouncementQueue();
}

function currentAnnouncementEvent() {
  const announcementEvents = paEligibleAnnouncementEvents();
  return (
    announcementEvents.find(
      (event) => minutesFromEvent(event) >= state.currentMinutes,
    ) ||
    null
  );
}

function currentAnnouncementEvents() {
  const events =
    state.mode === "station" && state.stationEvents.length > 0
      ? state.stationEvents
      : state.trainEvents;
  return events
    .filter((event) => event.type === "Arrival" || event.type === "Departure")
    .sort((a, b) => minutesFromEvent(a) - minutesFromEvent(b));
}

function upcomingAnnouncementEvents(limit = 8) {
  const events = currentAnnouncementEvents();
  const upcoming = events.filter(
    (event) => minutesFromEvent(event) >= state.currentMinutes,
  );
  return (upcoming.length ? upcoming : events).slice(0, limit);
}

function paEligibleAnnouncementEvents(limit = 8) {
  const events = currentAnnouncementEvents();
  const upcoming = events.filter((event) => {
    const delta = minutesFromEvent(event) - state.currentMinutes;
    return delta >= 0 && delta <= PA_LOOKAHEAD_MINUTES;
  });
  return upcoming.slice(0, limit);
}

function setActiveAnnouncement(event, scope) {
  state.activeAnnouncementKey = event ? announcementKey(event, scope) : null;
  state.activeStationEvent = event || null;
  renderDetails();
}

function nearestStationEvent() {
  const events =
    state.mode === "station" && state.stationEvents.length > 0
      ? state.stationEvents
      : state.trainEvents;
  const candidates = events.filter(
    (event) => event.type === "Arrival" || event.type === "Departure",
  );
  if (state.activeStationEvent) {
    return state.activeStationEvent;
  }
  return candidates.reduce((nearest, event) => {
    if (!nearest) {
      return event;
    }
    const eventDelta = Math.abs(minutesFromEvent(event) - state.currentMinutes);
    const nearestDelta = Math.abs(minutesFromEvent(nearest) - state.currentMinutes);
    return eventDelta < nearestDelta ? event : nearest;
  }, null);
}

function stationTrainAnimation(event) {
  if (!event) {
    return null;
  }
  const eventMinute = minutesFromEvent(event);
  const delta = state.currentMinutes - eventMinute;
  if (event.type === "Arrival") {
    if (delta < -6 || delta > 12) {
      return null;
    }
    if (delta < 0) {
      return { event, phase: "arriving", progress: Math.max(0, Math.min(1, (delta + 6) / 6)) };
    }
    return { event, phase: "dwell", progress: Math.max(0, Math.min(1, delta / 12)) };
  }
  if (delta < -10 || delta > 6) {
    return null;
  }
  if (delta < 0) {
    return { event, phase: "boarding", progress: Math.max(0, Math.min(1, (delta + 10) / 10)) };
  }
  return { event, phase: "departing", progress: Math.max(0, Math.min(1, delta / 6)) };
}

function crossedEventWindow(event) {
  const eventMinute = minutesFromEvent(event);
  if (state.currentMinutes >= state.previousMinutes) {
    return eventMinute >= state.previousMinutes && eventMinute <= state.currentMinutes;
  }
  return eventMinute <= state.currentMinutes;
}

function triggerStationAnnouncements(position) {
  if (!state.playing || !state.soundEnabled) {
    return;
  }

  const events =
    state.mode === "station"
      ? state.stationEvents
      : state.trainEvents.filter((event) => event.stationCode);
  const scope = announcementScope();

  events
    .filter((event) => event.type !== "Transit" && crossedEventWindow(event))
    .slice(0, 3)
    .forEach((event) => enqueueAnnouncement(event, scope));

  if (state.mode === "train" && position?.isStopped) {
    [position.previous, position.next]
      .filter((event) => event && event.type !== "Transit")
      .forEach((event) => enqueueAnnouncement(event, scope));
  }
}

function runAutoPaLoop(now) {
  if (
    !state.soundEnabled ||
    !state.autoPaEnabled ||
    state.announcementBusy ||
    state.announcementQueue.length > 0
  ) {
    return;
  }
  if (now - state.autoPaLastAt < 22000) {
    return;
  }

  const events = paEligibleAnnouncementEvents();
  if (events.length === 0) {
    return;
  }
  const event = events[state.autoPaIndex % events.length];
  state.autoPaIndex += 1;
  state.autoPaLastAt = now;
  queueAnnouncementForEvent(event);
}

function queueAnnouncementForEvent(event) {
  if (!event) {
    return;
  }
  state.announcementQueue = [
    { event, scope: announcementScope(), texts: announcementTexts(event) },
  ];
  state.announcementBusy = false;
  processAnnouncementQueue();
}

function resetCrowd() {
  const station = stationPoint(state.selectedStationCode) || {
    x: els.canvas.width * 0.52,
    y: els.canvas.height * 0.58,
  };
  state.people = Array.from({ length: 34 }, (_, index) => ({
    x: station.x + (Math.random() - 0.5) * 280,
    y: station.y + 44 + Math.random() * 150,
    speed: 14 + Math.random() * 42,
    direction: Math.random() > 0.5 ? 1 : -1,
    color: ["#e85d75", "#4db6ac", "#f2c14e", "#6fa8dc", "#f7a072"][index % 5],
  }));
  state.vendors = Array.from({ length: 5 }, (_, index) => ({
    x: station.x - 170 + index * 84,
    y: station.y + 96 + Math.random() * 34,
    color: ["#d8654f", "#e6c15d", "#4db6ac", "#c98b5b", "#8ab17d"][index],
  }));
}

function currentTrainPosition() {
  const train = state.trains[state.selectedTrainNo];
  if (!train || state.trainEvents.length === 0) {
    return null;
  }

  const routePoints = train.mappedRoute.map(stationPoint).filter(Boolean);
  if (routePoints.length === 0) {
    return null;
  }

  let previous = state.trainEvents[0];
  let next = state.trainEvents[state.trainEvents.length - 1];
  for (let index = 0; index < state.trainEvents.length - 1; index += 1) {
    const a = state.trainEvents[index];
    const b = state.trainEvents[index + 1];
    if (
      minutesFromEvent(a) <= state.currentMinutes &&
      minutesFromEvent(b) >= state.currentMinutes
    ) {
      previous = a;
      next = b;
      break;
    }
  }

  const previousPoint =
    stationPoint(previous.stationCode) ||
    stationPoint(previous.sourceStationCode) ||
    routePoints[0];
  const nextPoint =
    stationPoint(next.stationCode) ||
    stationPoint(previous.destinationStationCode) ||
    previousPoint;
  const span = Math.max(1, minutesFromEvent(next) - minutesFromEvent(previous));
  const progress = Math.max(
    0,
    Math.min(1, (state.currentMinutes - minutesFromEvent(previous)) / span),
  );
  const isStopped =
    previous.stationCode === next.stationCode ||
    previous.type === "Arrival" ||
    next.type === "Departure";

  return {
    x: previousPoint.x + (nextPoint.x - previousPoint.x) * progress,
    y: previousPoint.y + (nextPoint.y - previousPoint.y) * progress,
    previous,
    next,
    progress,
    routePoints,
    isStopped,
  };
}

function drawBackground() {
  const width = els.canvas.width;
  const height = els.canvas.height;
  const gradient = ctx.createLinearGradient(0, 0, width, height);
  gradient.addColorStop(0, "#17201d");
  gradient.addColorStop(0.5, "#121614");
  gradient.addColorStop(1, "#1d1813");
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, width, height);

  ctx.save();
  ctx.globalAlpha = 0.16;
  ctx.strokeStyle = "#f6f1e8";
  ctx.lineWidth = 1;
  for (let x = 0; x < width; x += 70) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x - 180, height);
    ctx.stroke();
  }
  ctx.restore();
}

function drawIndiaOutline() {
  ctx.save();
  ctx.beginPath();
  const bounds = activeMapBounds();
  INDIA_OUTLINE.forEach(([lon, lat], index) => {
    const point = projectPoint(lat, lon, bounds);
    if (index === 0) {
      ctx.moveTo(point.x, point.y);
    } else {
      ctx.lineTo(point.x, point.y);
    }
  });
  ctx.closePath();
  ctx.fillStyle = "rgba(79, 100, 70, 0.35)";
  ctx.fill();
  ctx.strokeStyle = "rgba(246, 241, 232, 0.36)";
  ctx.lineWidth = 2;
  ctx.stroke();
  ctx.restore();
}

function drawRoute(routePoints) {
  if (!routePoints || routePoints.length < 2) {
    return;
  }
  ctx.save();
  ctx.strokeStyle = "rgba(230, 193, 93, 0.78)";
  ctx.lineWidth = 4;
  ctx.lineJoin = "round";
  ctx.lineCap = "round";
  ctx.beginPath();
  routePoints.forEach((point, index) => {
    if (index === 0) {
      ctx.moveTo(point.x, point.y);
    } else {
      ctx.lineTo(point.x, point.y);
    }
  });
  ctx.stroke();

  routePoints.forEach((point, index) => {
    ctx.fillStyle = index === 0 ? "#4db6ac" : "#f6f1e8";
    ctx.beginPath();
    ctx.arc(point.x, point.y, index === 0 ? 7 : 4.5, 0, Math.PI * 2);
    ctx.fill();
  });
  ctx.restore();
}

function drawTrain(position) {
  if (!position) {
    return;
  }
  const pulse = Math.sin(performance.now() / 160) * 2;
  ctx.save();
  ctx.strokeStyle = "rgba(230, 193, 93, 0.35)";
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.arc(position.x, position.y, 34 + pulse * 2, 0, Math.PI * 2);
  ctx.stroke();
  ctx.restore();

  ctx.save();
  ctx.translate(position.x, position.y);
  ctx.fillStyle = "#d8654f";
  ctx.strokeStyle = "#f6f1e8";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.roundRect(-30, -15 + pulse, 60, 30, 8);
  ctx.fill();
  ctx.stroke();
  ctx.fillStyle = "#221f1b";
  ctx.fillRect(-18, -7 + pulse, 11, 10);
  ctx.fillRect(1, -7 + pulse, 11, 10);
  ctx.fillStyle = "#e6c15d";
  ctx.beginPath();
  ctx.arc(24, 9 + pulse, 5, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();

  ctx.save();
  ctx.fillStyle = "#f6f1e8";
  ctx.font = "600 15px system-ui";
  ctx.fillText(
    `${position.next.type} ${position.next.stationCode || ""}`,
    position.x + 28,
    position.y - 20,
  );
  ctx.restore();
}

function drawStationScene(deltaSeconds, stationCode = state.selectedStationCode) {
  const station = stationPoint(stationCode) || {
    x: els.canvas.width * 0.5,
    y: els.canvas.height * 0.48,
  };
  const trainAnimation = stationTrainAnimation(nearestStationEvent());
  ctx.save();
  ctx.translate(station.x, station.y);
  ctx.fillStyle = "#2a2722";
  ctx.fillRect(-260, 0, 520, 170);
  ctx.fillStyle = "#333126";
  ctx.fillRect(-260, -26, 520, 26);
  ctx.fillStyle = "#e6c15d";
  ctx.fillRect(-242, -58, 230, 39);
  ctx.fillStyle = "#18120a";
  ctx.font = "700 17px system-ui";
  ctx.fillText(stationCode || "STN", -230, -34);
  if (trainAnimation) {
    ctx.font = "600 12px system-ui";
    ctx.fillText(
      `PF ${platformForEvent(trainAnimation.event)} · ${trainAnimation.event.type} ${trainAnimation.event.trainNo}`,
      -124,
      -34,
    );
  }

  ctx.strokeStyle = "#d7d0c4";
  ctx.lineWidth = 4;
  for (let y = 102; y <= 136; y += 28) {
    ctx.beginPath();
    ctx.moveTo(-300, y);
    ctx.lineTo(300, y);
    ctx.stroke();
  }
  drawPlatformTrain(trainAnimation);
  ctx.restore();

  state.vendors.forEach((vendor) => {
    ctx.fillStyle = vendor.color;
    ctx.fillRect(vendor.x - 18, vendor.y - 18, 36, 20);
    ctx.fillStyle = "#f6f1e8";
    ctx.fillRect(vendor.x - 24, vendor.y - 24, 48, 8);
  });

  state.people.forEach((person) => {
    person.x += person.direction * person.speed * deltaSeconds;
    if (person.x < station.x - 280 || person.x > station.x + 280) {
      person.direction *= -1;
    }
    ctx.fillStyle = person.color;
    ctx.beginPath();
    ctx.arc(person.x, person.y - 14, 5, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillRect(person.x - 4, person.y - 9, 8, 18);
  });
}

function drawPlatformTrain(animation) {
  if (!animation) {
    return;
  }
  const { event, phase, progress } = animation;
  const easing = progress * progress * (3 - 2 * progress);
  let x = -30;
  if (phase === "arriving") {
    x = -420 + easing * 390;
  } else if (phase === "departing") {
    x = -30 + easing * 430;
  }
  const y = 92;
  const carCount = 4;
  const carWidth = 72;
  const carHeight = 30;

  ctx.save();
  ctx.translate(x, y);
  for (let index = 0; index < carCount; index += 1) {
    const carX = index * (carWidth + 6);
    ctx.fillStyle = index === 0 ? "#b94335" : "#c35642";
    ctx.beginPath();
    ctx.roundRect(carX, -carHeight, carWidth, carHeight, 6);
    ctx.fill();
    ctx.strokeStyle = "#f6f1e8";
    ctx.lineWidth = 1.5;
    ctx.stroke();

    ctx.fillStyle = "#221f1b";
    for (let windowIndex = 0; windowIndex < 3; windowIndex += 1) {
      ctx.fillRect(carX + 12 + windowIndex * 17, -23, 10, 9);
    }

    ctx.fillStyle = "#171412";
    ctx.beginPath();
    ctx.arc(carX + 15, 1, 5, 0, Math.PI * 2);
    ctx.arc(carX + carWidth - 15, 1, 5, 0, Math.PI * 2);
    ctx.fill();
  }

  ctx.fillStyle = "#e6c15d";
  ctx.font = "700 13px system-ui";
  ctx.fillText(`${event.trainNo}`, 14, -40);
  ctx.fillStyle = "#f6f1e8";
  ctx.font = "600 12px system-ui";
  ctx.fillText(
    phase === "arriving"
      ? "ARRIVING"
      : phase === "departing"
        ? "DEPARTING"
        : "AT PLATFORM",
    78,
    -40,
  );
  ctx.restore();
}

function renderScene(deltaSeconds) {
  drawBackground();
  drawIndiaOutline();

  if (state.mode === "train") {
    const position = currentTrainPosition();
    drawRoute(position?.routePoints);
    drawTrain(position);
    if (position?.isStopped) {
      drawStationScene(
        deltaSeconds,
        position.next.stationCode || position.previous.stationCode,
      );
    }
  } else {
    const station = stationPoint(state.selectedStationCode);
    drawStationScene(deltaSeconds);
    if (station) {
      ctx.save();
      ctx.fillStyle = "#4db6ac";
      ctx.beginPath();
      ctx.arc(station.x, station.y, 9, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    }
  }
}

function tick(now) {
  const deltaSeconds = Math.min(0.08, (now - state.lastFrameAt) / 1000);
  state.lastFrameAt = now;

  state.previousMinutes = state.currentMinutes;
  if (state.playing) {
    state.currentMinutes += (deltaSeconds * state.speed) / 60;
  }

  const position = currentTrainPosition();
  els.clockLabel.textContent = formatClock(state.currentMinutes);
  els.clockStatus.textContent = state.playing ? `${state.speed}x` : "Paused";
  syncTimelineControls();
  updateAudio(position);
  triggerStationAnnouncements(position);
  runAutoPaLoop(now);
  renderScene(deltaSeconds);
  requestAnimationFrame(tick);
}

function createAudio() {
  const AudioContextClass = window.AudioContext || window.webkitAudioContext;
  if (!AudioContextClass) {
    throw new Error("Web Audio is not supported in this browser.");
  }

  const audioContext = new AudioContextClass();
  const compressor = audioContext.createDynamicsCompressor();
  compressor.threshold.value = -22;
  compressor.knee.value = 24;
  compressor.ratio.value = 8;
  compressor.attack.value = 0.005;
  compressor.release.value = 0.2;
  compressor.connect(audioContext.destination);

  const master = audioContext.createGain();
  master.gain.value = 0.72;
  master.connect(compressor);

  const trainGain = audioContext.createGain();
  trainGain.gain.value = 0;
  trainGain.connect(master);

  const stationGain = audioContext.createGain();
  stationGain.gain.value = 0;
  stationGain.connect(master);

  const railOsc = audioContext.createOscillator();
  const railPulse = audioContext.createOscillator();
  const railPulseGain = audioContext.createGain();
  railOsc.type = "sawtooth";
  railOsc.frequency.value = 86;
  railPulse.type = "square";
  railPulse.frequency.value = 9.5;
  railPulseGain.gain.value = 26;
  railPulse.connect(railPulseGain).connect(railOsc.frequency);
  railOsc.connect(trainGain);
  railOsc.start();
  railPulse.start();

  const hornOsc = audioContext.createOscillator();
  const hornGain = audioContext.createGain();
  hornOsc.type = "triangle";
  hornOsc.frequency.value = 330;
  hornGain.gain.value = 0.08;
  hornOsc.connect(hornGain).connect(trainGain);
  hornOsc.start();

  const announcementOsc = audioContext.createOscillator();
  const announcementLfo = audioContext.createOscillator();
  const announcementLfoGain = audioContext.createGain();
  announcementOsc.type = "triangle";
  announcementOsc.frequency.value = 190;
  announcementLfo.frequency.value = 1.7;
  announcementLfoGain.gain.value = 55;
  announcementLfo.connect(announcementLfoGain).connect(announcementOsc.frequency);
  announcementOsc.connect(stationGain);
  announcementOsc.start();
  announcementLfo.start();

  const noiseBuffer = audioContext.createBuffer(
    1,
    audioContext.sampleRate * 2,
    audioContext.sampleRate,
  );
  const noise = noiseBuffer.getChannelData(0);
  for (let index = 0; index < noise.length; index += 1) {
    noise[index] = Math.random() * 2 - 1;
  }

  const stationNoise = audioContext.createBufferSource();
  const stationFilter = audioContext.createBiquadFilter();
  const stationNoiseGain = audioContext.createGain();
  stationNoise.buffer = noiseBuffer;
  stationNoise.loop = true;
  stationFilter.type = "bandpass";
  stationFilter.frequency.value = 820;
  stationFilter.Q.value = 0.55;
  stationNoiseGain.gain.value = 0.36;
  stationNoise.connect(stationFilter).connect(stationNoiseGain).connect(stationGain);
  stationNoise.start();

  const trainNoise = audioContext.createBufferSource();
  const trainFilter = audioContext.createBiquadFilter();
  const trainNoiseGain = audioContext.createGain();
  trainNoise.buffer = noiseBuffer;
  trainNoise.loop = true;
  trainFilter.type = "lowpass";
  trainFilter.frequency.value = 560;
  trainNoiseGain.gain.value = 0.22;
  trainNoise.connect(trainFilter).connect(trainNoiseGain).connect(trainGain);
  trainNoise.start();

  const announcementGain = audioContext.createGain();
  announcementGain.gain.value = 0.9;
  announcementGain.connect(master);

  return { audioContext, trainGain, stationGain, announcementGain };
}

function playAnnouncementChime() {
  return new Promise((resolve) => {
    if (!state.audio) {
      resolve();
      return;
    }

    const { audioContext, announcementGain } = state.audio;
    const now = audioContext.currentTime;
    [660, 880, 660].forEach((frequency, index) => {
      const osc = audioContext.createOscillator();
      const gain = audioContext.createGain();
      const start = now + index * 0.18;
      osc.type = "sine";
      osc.frequency.value = frequency;
      gain.gain.setValueAtTime(0.001, start);
      gain.gain.linearRampToValueAtTime(0.28, start + 0.025);
      gain.gain.exponentialRampToValueAtTime(0.001, start + 0.16);
      osc.connect(gain).connect(announcementGain);
      osc.start(start);
      osc.stop(start + 0.18);
    });
    window.setTimeout(resolve, 620);
  });
}

function voiceForLanguage(language) {
  const voices = window.speechSynthesis?.getVoices?.() || [];
  const normalized = language.toLowerCase();
  if (normalized.startsWith("hi")) {
    return (
      voices.find((candidate) => candidate.lang?.toLowerCase().startsWith("hi")) ||
      voices.find((candidate) => candidate.lang?.toLowerCase().startsWith("en-in")) ||
      voices.find((candidate) => candidate.lang?.toLowerCase().startsWith("en"))
    );
  }
  return (
    voices.find((candidate) => candidate.lang?.toLowerCase().startsWith("en-in")) ||
    voices.find((candidate) => candidate.lang?.toLowerCase().startsWith("en"))
  );
}

function speakAnnouncement(text, language) {
  return new Promise((resolve) => {
    if (!("speechSynthesis" in window) || !window.SpeechSynthesisUtterance) {
      resolve();
      return;
    }

    const utterance = new SpeechSynthesisUtterance(text);
    const voice = voiceForLanguage(language);
    if (voice) {
      utterance.voice = voice;
      utterance.lang = voice.lang;
    } else {
      utterance.lang = language;
    }
    utterance.rate = language.startsWith("hi") ? 0.86 : 0.92;
    utterance.pitch = 1.02;
    utterance.volume = 1;
    utterance.onend = resolve;
    utterance.onerror = resolve;
    window.speechSynthesis.speak(utterance);
  });
}

async function processAnnouncementQueue() {
  if (state.announcementBusy || !state.soundEnabled) {
    return;
  }
  const item = state.announcementQueue.shift();
  if (!item) {
    return;
  }
  state.announcementBusy = true;
  setActiveAnnouncement(item.event, item.scope || announcementScope());
  await playAnnouncementChime();
  await speakAnnouncement(item.texts.english, "en-IN");
  await speakAnnouncement(item.texts.hindi, "hi-IN");
  state.announcementBusy = false;
  setActiveAnnouncement(null);
  processAnnouncementQueue();
}

function updateAudio(position) {
  if (!state.audio) {
    return;
  }
  const now = state.audio.audioContext.currentTime;
  const stationDominant = state.mode === "station" || position?.isStopped;
  const ducking = state.announcementBusy ? 0.18 : 1;
  const trainVolume = 0;
  const stationVolume = 0;
  state.audio.trainGain.gain.setTargetAtTime(trainVolume, now, 0.05);
  state.audio.stationGain.gain.setTargetAtTime(stationVolume, now, 0.05);
  updateStationAmbience(stationDominant, ducking);
  updateTrainTravelSound(!stationDominant && state.playing, ducking);
  state.soundStatus = !state.soundEnabled
    ? "silent"
    : stationDominant
      ? "station"
      : state.playing
        ? "train"
        : "ready";
  els.soundButton.textContent = state.soundEnabled
    ? `${state.soundStatus[0].toUpperCase()}${state.soundStatus.slice(1)} Sound`
    : "Enable Sound";
}

function shuffledTrainSounds() {
  const sounds = [...TRAIN_SOUND_POOL];
  for (let index = sounds.length - 1; index > 0; index -= 1) {
    const swapIndex = Math.floor(Math.random() * (index + 1));
    [sounds[index], sounds[swapIndex]] = [sounds[swapIndex], sounds[index]];
  }
  if (sounds[0] === state.currentTrainSound && sounds.length > 1) {
    [sounds[0], sounds[1]] = [sounds[1], sounds[0]];
  }
  return sounds;
}

function nextTrainSound() {
  if (state.trainSoundQueue.length === 0) {
    state.trainSoundQueue = shuffledTrainSounds();
  }
  return state.trainSoundQueue.shift();
}

function loadTrainTravelSound(src) {
  if (state.trainTravelAudio) {
    state.trainTravelAudio.pause();
  }
  const audio = new Audio(src);
  audio.loop = false;
  audio.volume = 0;
  audio.addEventListener("ended", () => {
    if (state.soundEnabled && state.playing && state.mode === "train") {
      loadTrainTravelSound(nextTrainSound());
      state.trainTravelAudio.play().catch(() => {});
    }
  });
  state.trainTravelAudio = audio;
  state.currentTrainSound = src;
}

function updateTrainTravelSound(shouldMove, ducking) {
  if (!state.soundEnabled || !shouldMove) {
    if (state.trainTravelAudio && !state.trainTravelAudio.paused) {
      state.trainTravelAudio.pause();
    }
    return;
  }

  if (!state.trainTravelAudio || state.trainTravelAudio.ended) {
    loadTrainTravelSound(nextTrainSound());
  }
  state.trainTravelAudio.volume = 0.34 * ducking;
  if (state.trainTravelAudio.paused) {
    state.trainTravelAudio.play().catch(() => {});
  }
}

function updateStationAmbience(stationDominant, ducking) {
  const ambience = state.stationAmbienceAudio;
  if (!ambience) {
    return;
  }
  const shouldPlay = state.soundEnabled && stationDominant && state.playing;
  ambience.volume = shouldPlay ? 0.22 * ducking : 0;
  if (shouldPlay && ambience.paused) {
    ambience.play().catch(() => {});
  } else if (!shouldPlay && !ambience.paused) {
    ambience.pause();
  }
}

function loadStationAmbience(src) {
  const ambience = new Audio(src);
  ambience.loop = true;
  ambience.volume = 0;
  state.stationAmbienceAudio = ambience;
}

function bindEvents() {
  els.trainModeButton.addEventListener("click", () => setMode("train"));
  els.stationModeButton.addEventListener("click", () => setMode("station"));
  els.trainSearch.addEventListener("change", () => selectTrain(els.trainSearch.value));
  els.stationSearch.addEventListener("change", () => {
    selectStation(els.stationSearch.value);
  });
  els.playButton.addEventListener("click", () => {
    state.playing = !state.playing;
    els.playButton.textContent = state.playing ? "Pause" : "Play";
  });
  els.resetButton.addEventListener("click", resetClock);
  els.soundButton.addEventListener("click", async () => {
    try {
      if (!state.audio) {
        state.audio = createAudio();
      }
      await state.audio.audioContext.resume();
      state.soundEnabled = !state.soundEnabled;
      if (state.soundEnabled) {
        state.autoPaLastAt = 0;
        if (state.autoPaEnabled) {
          queueAnnouncementForEvent(currentAnnouncementEvent());
        }
      }
      if (!state.soundEnabled && "speechSynthesis" in window) {
        window.speechSynthesis.cancel();
        state.announcementQueue = [];
        state.announcementBusy = false;
        updateTrainTravelSound(false, 1);
      }
      updateAudio(currentTrainPosition());
    } catch (error) {
      console.error(error);
      state.soundEnabled = false;
      els.soundButton.textContent = "Audio Unavailable";
    }
  });
  els.autoPaButton.addEventListener("click", () => {
    state.autoPaEnabled = !state.autoPaEnabled;
    state.autoPaLastAt = 0;
    els.autoPaButton.classList.toggle("active", state.autoPaEnabled);
    els.autoPaButton.textContent = state.autoPaEnabled ? "Auto PA On" : "Auto PA Off";
  });
  els.ambienceFile.addEventListener("change", () => {
    const file = els.ambienceFile.files?.[0];
    if (!file) {
      return;
    }
    if (state.stationAmbienceUrl) {
      URL.revokeObjectURL(state.stationAmbienceUrl);
    }
    state.stationAmbienceUrl = URL.createObjectURL(file);
    loadStationAmbience(state.stationAmbienceUrl);
  });
  els.testAnnouncementButton.addEventListener("click", async () => {
    try {
      if (!state.audio) {
        state.audio = createAudio();
      }
      await state.audio.audioContext.resume();
      state.soundEnabled = true;
      queueAnnouncementForEvent(currentAnnouncementEvent());
      updateAudio(currentTrainPosition());
    } catch (error) {
      console.error(error);
      els.soundButton.textContent = "Audio Unavailable";
    }
  });
  function setSpeed(value) {
    state.speed = Number(value);
    els.speedSlider.value = String(state.speed);
    els.speedLabel.textContent = `${state.speed}x`;
    els.speedPresets.forEach((button) => {
      button.classList.toggle(
        "active",
        Number(button.dataset.speed) === state.speed,
      );
    });
  }

  els.speedSlider.addEventListener("input", () => {
    setSpeed(els.speedSlider.value);
  });
  els.speedPresets.forEach((button) => {
    button.addEventListener("click", () => setSpeed(button.dataset.speed));
  });
  els.timelineScrubber.addEventListener("input", () => {
    state.playing = false;
    els.playButton.textContent = "Play";
    setClockMinutes(Number(els.timelineScrubber.value));
  });
  els.prevEventButton.addEventListener("click", () => jumpToEvent(-1));
  els.nextEventButton.addEventListener("click", () => jumpToEvent(1));
  els.preAnnounceButton.addEventListener("click", jumpToPreAnnouncement);
  window.addEventListener("resize", () => {
    resizeCanvas();
    resetCrowd();
  });
}

async function main() {
  resizeCanvas();
  bindEvents();
  loadStationAmbience(DEFAULT_STATION_AMBIENCE);
  await loadInitialData();
  requestAnimationFrame(tick);
}

main().catch((error) => {
  console.error(error);
  els.primaryTitle.textContent = "Could not load data";
  els.primarySubtitle.textContent =
    "Open http://127.0.0.1:8000/web/ instead of the file:// URL so the browser can fetch JSON and enable audio reliably.";
});
