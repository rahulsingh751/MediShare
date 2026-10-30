document.addEventListener("DOMContentLoaded", () => {
  const menuToggle = document.querySelector(".menu-toggle");
  const navigation = document.querySelector("#primary-nav");
  if (menuToggle && navigation) {
    menuToggle.addEventListener("click", () => {
      const isOpen = menuToggle.getAttribute("aria-expanded") === "true";
      menuToggle.setAttribute("aria-expanded", String(!isOpen));
      navigation.classList.toggle("is-open", !isOpen);
    });
  }

  document.querySelectorAll("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (!window.confirm(form.dataset.confirm)) event.preventDefault();
    });
  });

  const imageInput = document.querySelector("#id_images");
  const preview = document.querySelector("#image-preview");
  if (imageInput && preview) {
    imageInput.addEventListener("change", () => {
      preview.replaceChildren();
      Array.from(imageInput.files || []).slice(0, 5).forEach((file) => {
        if (!file.type.startsWith("image/")) return;
        const image = document.createElement("img");
        image.alt = `Preview: ${file.name}`;
        image.src = URL.createObjectURL(file);
        image.addEventListener("load", () => URL.revokeObjectURL(image.src), { once: true });
        preview.append(image);
      });
    });
  }

  const search = document.querySelector("[data-suggestions-url]");
  const suggestions = document.querySelector("#search-suggestions");
  if (search && suggestions) {
    let timer;
    let controller;
    const hideSuggestions = () => {
      suggestions.hidden = true;
      suggestions.replaceChildren();
    };

    search.addEventListener("input", () => {
      window.clearTimeout(timer);
      if (controller) controller.abort();
      if (search.value.trim().length < 2) {
        hideSuggestions();
        return;
      }
      timer = window.setTimeout(async () => {
        controller = new AbortController();
        try {
          const url = new URL(search.dataset.suggestionsUrl, window.location.origin);
          url.searchParams.set("q", search.value.trim());
          const response = await fetch(url, {
            headers: { Accept: "application/json" },
            credentials: "same-origin",
            signal: controller.signal,
          });
          if (!response.ok) throw new Error("Suggestions could not be loaded.");
          const data = await response.json();
          suggestions.replaceChildren();
          data.suggestions.forEach((item) => {
            const option = document.createElement("button");
            option.type = "button";
            option.className = "suggestion-option";
            option.setAttribute("role", "option");
            option.textContent = item.label;
            option.addEventListener("click", () => {
              search.value = item.query;
              hideSuggestions();
              search.form.requestSubmit();
            });
            suggestions.append(option);
          });
          suggestions.hidden = data.suggestions.length === 0;
        } catch (error) {
          if (error.name !== "AbortError") {
            suggestions.replaceChildren();
            const status = document.createElement("span");
            status.className = "suggestion-option";
            status.setAttribute("role", "status");
            status.textContent = "Suggestions are unavailable. You can still submit your search.";
            suggestions.append(status);
            suggestions.hidden = false;
          }
        }
      }, 180);
    });

    search.addEventListener("keydown", (event) => {
      if (event.key === "Escape") hideSuggestions();
    });
    document.addEventListener("click", (event) => {
      if (!suggestions.contains(event.target) && event.target !== search) hideSuggestions();
    });
  }
});
