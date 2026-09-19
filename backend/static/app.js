document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll("form").forEach(function (form) {
    form.addEventListener("submit", function () {
      var button = form.querySelector("button[type='submit'], input[type='submit']");
      if (button) {
        button.setAttribute("aria-busy", "true");
      }
    });
  });
});
