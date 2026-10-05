const menuButton = document.querySelector(".menu-button");
const navigation = document.querySelector(".site-nav");

if (menuButton && navigation) {
  const closeNavigation = (restoreFocus = false) => {
    navigation.classList.remove("is-open");
    menuButton.setAttribute("aria-expanded", "false");

    if (restoreFocus) {
      menuButton.focus();
    }
  };

  menuButton.addEventListener("click", () => {
    const open = navigation.classList.toggle("is-open");
    menuButton.setAttribute("aria-expanded", String(open));
  });

  navigation.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", () => {
      closeNavigation();
    });
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && navigation.classList.contains("is-open")) {
      closeNavigation(true);
    }
  });

  window.addEventListener("resize", () => {
    if (window.matchMedia("(min-width: 901px)").matches) {
      closeNavigation();
    }
  });
}

const year = document.querySelector("#year");
if (year) {
  year.textContent = new Date().getFullYear();
}


/* PERFORMANCE — defer below-fold Discovery artwork until it is near the viewport. */
const discoverySection = document.querySelector("#discovery");

if (discoverySection) {
  const revealDiscoveryImages = () => {
    discoverySection.classList.add("images-ready");
  };

  if ("IntersectionObserver" in window) {
    const discoveryObserver = new IntersectionObserver(
      (entries, observer) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          revealDiscoveryImages();
          observer.disconnect();
        }
      },
      { rootMargin: "700px 0px" }
    );

    discoveryObserver.observe(discoverySection);
  } else {
    revealDiscoveryImages();
  }
}
