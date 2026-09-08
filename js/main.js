/* Felicity - header interactions: burger menu, mobile search, search suggestions. */
(function () {
  "use strict";

  function relPath(path) {
    var depth = document.body.getAttribute("data-depth") || "0";
    var prefix = depth === "2" ? "../../" : depth === "1" ? "../" : "";
    return prefix + path;
  }

  function fmtPrice(v) {
    return String(v).replace(/\B(?=(\d{3})+(?!\d))/g, " ") + " ₴";
  }

  function escapeHtml(str) {
    var div = document.createElement("div");
    div.textContent = str == null ? "" : String(str);
    return div.innerHTML;
  }

  // Product card markup for the homepage sections (depth 0, root-relative
  // paths). Mirrors product_card_html() in generate.py so styling and the
  // delegated add-to-cart handler in cart.js keep working.
  function homeCard(p) {
    var badge = "";
    if (!p.inStock) badge = '<span class="badge badge-out">Розпродано</span>';
    else if (p.discount) badge = '<span class="badge badge-sale">-' + p.discount + "%</span>";

    var priceHtml = '<span class="price-current">' + fmtPrice(p.price) + "</span>";
    if (p.oldPrice) priceHtml += '<span class="price-old">' + fmtPrice(p.oldPrice) + "</span>";

    var btnDisabled = p.inStock ? "" : " disabled";
    var btnLabel = p.inStock ? "Додати в кошик" : "Немає в наявності";
    var alt = escapeHtml(p.name) + " - " + escapeHtml(p.categoryName) + " Felicity";

    return (
      '<article class="product-card" data-product-card data-price="' + p.price +
        '" data-instock="' + (p.inStock ? "true" : "false") + '">' +
      badge +
      '<a class="product-media" href="' + p.url + '" tabindex="-1" aria-hidden="true">' +
        '<img src="' + p.image + '" width="600" height="600" alt="' + alt + '" loading="lazy">' +
      "</a>" +
      '<p class="product-cat"><a href="category/' + p.category + '/">' + escapeHtml(p.categoryName) + "</a></p>" +
      '<h3 class="product-title"><a href="' + p.url + '">' + escapeHtml(p.name) + "</a></h3>" +
      '<div class="product-price">' + priceHtml + "</div>" +
      '<button type="button" class="btn btn-primary btn-block" data-add-to-cart="' + p.id + '"' +
        btnDisabled + ">" + btnLabel + "</button>" +
      "</article>"
    );
  }

  // Contact / checkout forms: send to the configured endpoint (Google Apps Script)
  function sendLead(payload) {
    var endpoint = window.FELICITY_FORM_ENDPOINT;
    if (!endpoint) return;
    fetch(endpoint, {
      method: "POST",
      mode: "no-cors",
      headers: { "Content-Type": "text/plain" },
      body: JSON.stringify(payload),
    }).catch(function () {});
  }
  window.FelicityLeads = { send: sendLead };

  document.addEventListener("DOMContentLoaded", function () {
    var burger = document.querySelector("[data-burger]");
    var nav = document.querySelector("[data-main-nav]");

    if (burger && nav) {
      burger.addEventListener("click", function () {
        var isOpen = nav.classList.toggle("open");
        burger.setAttribute("aria-expanded", isOpen ? "true" : "false");
      });
    }

    // Search suggestions (desktop + mobile inputs)
    var searchInputs = document.querySelectorAll("[data-search-input]");
    var products = window.FELICITY_PRODUCTS || [];

    // Homepage sections: replace the static first-4 with a random 4 drawn from
    // the whole category, reshuffled on every page load. Category/catalog pages
    // use [data-product-grid] (handled by catalog.js) and are left untouched.
    var homeGrids = document.querySelectorAll("[data-home-grid]");
    if (homeGrids.length && products.length) {
      homeGrids.forEach(function (grid) {
        var slug = grid.getAttribute("data-home-grid");
        var count = Number(grid.getAttribute("data-home-count")) || 4;
        var pool = products.filter(function (p) { return p.category === slug; });
        if (pool.length === 0) return; // keep the server-rendered fallback
        for (var i = pool.length - 1; i > 0; i--) {
          var j = Math.floor(Math.random() * (i + 1));
          var tmp = pool[i]; pool[i] = pool[j]; pool[j] = tmp;
        }
        grid.innerHTML = pool.slice(0, count).map(homeCard).join("");
      });
    }

    searchInputs.forEach(function (input) {
      var wrap = input.closest("[data-search-wrap]");
      var results = wrap ? wrap.querySelector("[data-search-results]") : null;
      if (!results) return;

      input.addEventListener("input", function () {
        var q = input.value.trim().toLowerCase();
        if (q.length < 2) {
          results.classList.remove("open");
          results.innerHTML = "";
          return;
        }
        var matches = products
          .filter(function (p) { return p.name.toLowerCase().indexOf(q) !== -1; })
          .slice(0, 6);

        if (matches.length === 0) {
          results.innerHTML = '<div style="padding:12px 14px; font-size:0.9rem; color:var(--color-text-muted);">Нічого не знайдено</div>';
          results.classList.add("open");
          return;
        }

        results.innerHTML = matches.map(function (p) {
          return (
            '<a href="' + relPath(p.url) + '">' +
            "<span>" + p.name + "</span>" +
            '<span class="sugg-price">' + p.price.toLocaleString("uk-UA") + " ₴</span>" +
            "</a>"
          );
        }).join("");
        results.classList.add("open");
      });

      document.addEventListener("click", function (e) {
        if (!wrap.contains(e.target)) {
          results.classList.remove("open");
        }
      });

      var form = input.closest("form");
      if (form) {
        form.addEventListener("submit", function (e) {
          e.preventDefault();
          var q = input.value.trim().toLowerCase();
          var match = products.find(function (p) { return p.name.toLowerCase().indexOf(q) !== -1; });
          if (match) window.location.href = relPath(match.url);
        });
      }
    });

    // Product gallery: click/keyboard through thumbnails
    var gallery = document.querySelector("[data-gallery]");
    if (gallery) {
      var mainImg = gallery.querySelector("[data-gallery-main]");
      var thumbs = Array.prototype.slice.call(gallery.querySelectorAll("[data-gallery-thumb]"));
      var counter = gallery.querySelector("[data-gallery-counter]");
      var current = 0;

      function show(index) {
        if (thumbs.length === 0) return;
        current = (index + thumbs.length) % thumbs.length;
        var thumb = thumbs[current];
        mainImg.src = thumb.getAttribute("data-src");
        thumbs.forEach(function (t) { t.classList.remove("active"); });
        thumb.classList.add("active");
        if (counter) counter.textContent = (current + 1) + " / " + thumbs.length;
      }

      thumbs.forEach(function (thumb, i) {
        thumb.addEventListener("click", function () { show(i); });
      });

      var prevBtn = gallery.querySelector("[data-gallery-prev]");
      var nextBtn = gallery.querySelector("[data-gallery-next]");
      if (prevBtn) prevBtn.addEventListener("click", function () { show(current - 1); });
      if (nextBtn) nextBtn.addEventListener("click", function () { show(current + 1); });

      gallery.addEventListener("keydown", function (e) {
        if (e.key === "ArrowLeft") show(current - 1);
        if (e.key === "ArrowRight") show(current + 1);
      });
    }

    // Homepage hero: auto-rotate banner photos
    var heroBanner = document.querySelector("[data-hero-banner]");
    if (heroBanner) {
      var slides = Array.prototype.slice.call(heroBanner.querySelectorAll(".hero-banner-img"));
      if (slides.length > 1) {
        var slide = 0;
        setInterval(function () {
          slides[slide].classList.remove("active");
          slide = (slide + 1) % slides.length;
          slides[slide].classList.add("active");
        }, 5000);
      }
    }

    var contactForm = document.querySelector("[data-contact-form]");
    if (contactForm) {
      contactForm.addEventListener("submit", function (e) {
        e.preventDefault();
        sendLead({
          form: "contact",
          name: contactForm.querySelector("[name=name]").value,
          phone: contactForm.querySelector("[name=phone]").value,
          message: contactForm.querySelector("[name=message]").value,
        });
        contactForm.reset();
        var note = contactForm.querySelector("[data-form-success]");
        if (note) note.style.display = "block";
      });
    }

    // Partnership form: serialize every named field and send as form "partner".
    var partnerForm = document.querySelector("[data-partner-form]");
    if (partnerForm) {
      partnerForm.addEventListener("submit", function (e) {
        e.preventDefault();
        var payload = { form: "partner" };
        partnerForm.querySelectorAll("[name]").forEach(function (field) {
          if ((field.type === "radio" || field.type === "checkbox") && !field.checked) return;
          payload[field.name] = field.value;
        });
        sendLead(payload);
        partnerForm.reset();
        var note = partnerForm.querySelector("[data-form-success]");
        if (note) note.style.display = "block";
      });
    }
  });
})();
