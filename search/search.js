const searchInput = document.querySelector("#search-query");
const searchForm = document.querySelector(".search-form");
const searchStatus = document.querySelector("#search-status");
const searchResults = document.querySelector("#search-results");
const formatButtons = Array.from(document.querySelectorAll(".search-format-filter"));

if (searchInput && searchForm && searchStatus && searchResults) {
  const normalize = (value) =>
    value
      .toLocaleLowerCase("en")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/[^a-z0-9]+/g, " ")
      .trim();

  const formatDate = (value) => {
    if (!value) return "";
    const parts = value.split("-");
    if (parts.length !== 3) return value;
    return `${parts[2]}.${parts[1]}.${parts[0]}`;
  };

  const scoreStory = (story, terms) => {
    const title = normalize(story.title);
    const description = normalize(story.description);
    const format = normalize(story.format);

    return terms.reduce((score, term) => {
      if (title.includes(term)) score += 8;
      if (format.includes(term)) score += 4;
      if (description.includes(term)) score += 2;
      return score;
    }, 0);
  };

  const createResult = (story) => {
    const link = document.createElement("a");
    link.className = "search-result";
    link.href = story.url;

    const meta = document.createElement("div");
    meta.className = "search-result-meta";

    const format = document.createElement("span");
    format.className = "search-result-format";
    format.textContent = story.format;
    meta.append(format);

    if (story.date) {
      const date = document.createElement("span");
      date.className = "search-result-date";
      date.textContent = formatDate(story.date);
      meta.append(date);
    }

    const title = document.createElement("h2");
    title.textContent = story.title;

    const description = document.createElement("p");
    description.textContent = story.description;

    link.append(meta, title, description);
    return link;
  };

  const formatDirectories = {
    "The Latest": "latest", "Discovery": "discovery",
    "Intelligence": "intelligence", "Editorial": "editorial"
  };
  const allowedFormats = new Set(Object.keys(formatDirectories));
  const isPublicStory = (story) => {
    if (!story || typeof story !== "object" || Array.isArray(story)) return false;
    if (!allowedFormats.has(story.format)) return false;
    if (typeof story.title !== "string" || !story.title.trim()) return false;
    if (typeof story.description !== "string" || !story.description.trim()) return false;
    if (typeof story.url !== "string") return false;
    const directory = formatDirectories[story.format];
    return new RegExp("^/" + directory + "/[a-z0-9]+(?:-[a-z0-9]+)*\\.html$").test(story.url);
  };

  let stories = [];
  let loaded = false;
  const parameters = new URLSearchParams(window.location.search);
  let activeFormat = allowedFormats.has(parameters.get("format")) ? parameters.get("format") : "all";

  const render = (rawQuery, updateUrl = true) => {
    const query = String(rawQuery || "").trim();
    const terms = normalize(query).split(" ").filter(Boolean);
    searchResults.replaceChildren();

    for (const button of formatButtons) {
      const format = button.dataset.format;
      const count = format === "all"
        ? stories.length : stories.filter((story) => story.format === format).length;
      button.textContent = `${format === "all" ? "All formats" : format} (${count})`;
      button.setAttribute("aria-pressed", String(activeFormat === format));
    }
    if (!loaded) return;

    if (updateUrl) {
      const url = new URL(window.location.href);
      if (query) url.searchParams.set("q", query);
      else url.searchParams.delete("q");
      if (activeFormat !== "all") url.searchParams.set("format", activeFormat);
      else url.searchParams.delete("format");
      window.history.replaceState({}, "", url);
    }

    const eligible = stories.filter((story) => activeFormat === "all" || story.format === activeFormat);
    const matches = eligible
      .map((story, index) => ({story, index, score: scoreStory(story, terms)}))
      .filter(({score}) => !terms.length || score > 0)
      .sort((a, b) => (terms.length ? b.score - a.score : 0) || a.index - b.index);

    const suffix = activeFormat === "all" ? "" : ` in ${activeFormat}`;
    searchStatus.textContent = terms.length
      ? `${matches.length} result${matches.length === 1 ? "" : "s"} for “${query}”${suffix}.`
      : `${matches.length} published stor${matches.length === 1 ? "y" : "ies"}${suffix}.`;
    matches.forEach(({story}) => searchResults.append(createResult(story)));
  };

  for (const button of formatButtons) {
    button.addEventListener("click", () => {
      const format = button.dataset.format;
      if (format !== "all" && !allowedFormats.has(format)) return;
      activeFormat = format;
      render(searchInput.value);
    });
  }

  fetch("search-index.json")
    .then((response) => {
      if (!response.ok) throw new Error("Search index unavailable");
      return response.json();
    })
    .then((data) => {
      if (!Array.isArray(data) || !data.every(isPublicStory)) throw new Error("Invalid public index");
      stories = data;
      loaded = true;
      const initialQuery = new URLSearchParams(window.location.search).get("q") || "";
      searchInput.value = initialQuery;
      render(initialQuery, false);
    })
    .catch(() => {
      for (const button of formatButtons) button.disabled = true;
      searchStatus.textContent = "Search is temporarily unavailable. Browse the section archives instead.";
    });

  searchForm.addEventListener("submit", (event) => {
    event.preventDefault();
    render(searchInput.value);
  });

  searchInput.addEventListener("input", () => {
    render(searchInput.value);
  });
}
