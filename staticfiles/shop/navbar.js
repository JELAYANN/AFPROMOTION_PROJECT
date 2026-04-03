// shop/static/shop/navbar.js

document.addEventListener("DOMContentLoaded", () => {
  const header = document.querySelector(".site-header");
  if (!header) return;

  const toggleHeader = () => {
    if (window.scrollY > 10) {
      header.classList.add("is-scrolled");
    } else {
      header.classList.remove("is-scrolled");
    }
  };

  // jalankan sekali saat load
  toggleHeader();
  // dan setiap scroll
  window.addEventListener("scroll", toggleHeader);
});
