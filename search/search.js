const searchInput = document.querySelector("#search-query");
const searchForm = document.querySelector(".search-form");
const searchStatus = document.querySelector("#search-status");
const searchResults = document.querySelector("#search-results");

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

  let stories = [];

  const render = (rawQuery, updateUrl = true) => {
    const query = rawQuery.trim();
    const terms = normalize(query).split(" ").filter(Boolean);
    searchResults.replaceChildren();

    if (updateUrl) {
      const url = new URL(window.location.href);
      if (query) {
        url.searchParams.set("q", query);
      } else {
        url.searchParams.delete("q");
      }
      window.history.replaceState({}, "", url);
    }

    if (!terms.length) {
      searchStatus.textContent = `Search ${stories.length} published stories.`;
      return;
    }

    const matches = stories
      .map((story, index) => ({story, index, score: scoreStory(story, terms)}))
      .filter(({score}) => score > 0)
      .sort((a, b) => b.score - a.score || a.index - b.index);

    searchStatus.textContent = `${matches.length} result${matches.length === 1 ? "" : "s"} for “${query}”.`;

    matches.forEach(({story}) => {
      searchResults.append(createResult(story));
    });
  };

  fetch("search-index.json")
    .then((response) => {
      if (!response.ok) throw new Error("Search index unavailable");
      return response.json();
    })
    .then((data) => {
      stories = Array.isArray(data) ? data : [];
      const initialQuery = new URLSearchParams(window.location.search).get("q") || "";
      searchInput.value = initialQuery;
      render(initialQuery, false);
    })
    .catch(() => {
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
