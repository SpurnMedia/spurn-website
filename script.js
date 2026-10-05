const menuButton = document.querySelector(".menu-button");
const navigation = document.querySelector(".site-nav");

if (menuButton && navigation) {
  menuButton.addEventListener("click", () => {
    const open = navigation.classList.toggle("is-open");
    menuButton.setAttribute("aria-expanded", String(open));
  });

  navigation.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", () => {
      navigation.classList.remove("is-open");
      menuButton.setAttribute("aria-expanded", "false");
    });
  });
}

const form = document.querySelector("#newsletter-form");
const message = document.querySelector("#form-message");

if (form && message) {
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    message.textContent = "The newsletter connection will be activated in the next step.";
    form.reset();
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
