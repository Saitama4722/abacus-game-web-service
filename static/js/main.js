/**
 * Abacus Game — global JS: tooltips, flash auto-dismiss, form Enter submit.
 */
(function () {
  'use strict';

  function initTooltips() {
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.forEach(function (el) {
      new bootstrap.Tooltip(el);
    });
  }

  function initFlashAutoDismiss() {
    var alerts = document.querySelectorAll('.flash-messages .alert');
    alerts.forEach(function (alert) {
      setTimeout(function () {
        var bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
        if (bsAlert) bsAlert.close();
      }, 6000);
    });
  }

  /* Forms submit on Enter by default; no extra handler needed. */

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      initTooltips();
      initFlashAutoDismiss();
    });
  } else {
    initTooltips();
    initFlashAutoDismiss();
  }
})();
