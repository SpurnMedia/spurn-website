const newsletterForm = document.querySelector("[data-newsletter-form]");
const newsletterStatus = document.querySelector("[data-newsletter-status]");

if (newsletterForm && newsletterStatus) {
  const config = window.SPURN_NEWSLETTER || {};
  const endpoint = typeof config.endpoint === "string" ? config.endpoint.trim() : "";
  const isEnabled = config.enabled === true && endpoint.length > 0;
  const emailInput = newsletterForm.querySelector('input[name="email"]');
  const honeypot = newsletterForm.querySelector('input[name="website"]');
  const submitButton = newsletterForm.querySelector('button[type="submit"]');

  const setStatus = (message) => {
    newsletterStatus.hidden = false;
    newsletterStatus.textContent = message;
  };

  if (isEnabled) {
    newsletterForm.hidden = false;
    newsletterStatus.hidden = true;

    newsletterForm.addEventListener("submit", async (event) => {
      event.preventDefault();

      if (!emailInput || !submitButton) return;

      if (!emailInput.checkValidity()) {
        emailInput.reportValidity();
        setStatus("Enter a valid email address.");
        return;
      }

      if (honeypot && honeypot.value) {
        newsletterForm.reset();
        setStatus("Thanks.");
        return;
      }

      newsletterForm.classList.add("is-submitting");
      submitButton.disabled = true;
      submitButton.setAttribute("aria-disabled", "true");

      try {
        const response = await fetch(endpoint, {
          method: "POST",
          body: new FormData(newsletterForm),
          headers: {
            Accept: "application/json"
          }
        });

        if (!response.ok) {
          throw new Error("Newsletter signup failed");
        }

        newsletterForm.reset();
        setStatus("You're on the list.");
      } catch {
        setStatus("That didn’t go through. Please try again.");
      } finally {
        newsletterForm.classList.remove("is-submitting");
        submitButton.disabled = false;
        submitButton.removeAttribute("aria-disabled");
      }
    });
  } else {
    newsletterForm.hidden = true;
    setStatus("Subscriptions are not open yet.");
  }
}
