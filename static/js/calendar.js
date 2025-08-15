document.addEventListener("DOMContentLoaded", function () {
  const calendarEl = document.getElementById("calendar");
  const calendar = new FullCalendar.Calendar(calendarEl, {
    initialView: "dayGridMonth",
    height: "auto",
    headerToolbar: {
      left: "prev,next today",
      center: "title",
      right: "dayGridMonth,dayGridWeek,dayGridDay"
    },
    navLinks: true,
    selectable: true,
    dayMaxEvents: true,
    eventDisplay: "block",
    events: "/api/events",
    dateClick: function(info) {
      // Open the entry page for that date
      window.location.href = `/entry?date=${info.dateStr}`;
    },
    eventClick: function(info) {
      // Also open the day by clicking on an event
      const dateStr = info.event.startStr.slice(0, 10);
      window.location.href = `/entry?date=${dateStr}`;
    }
  });
  calendar.render();
});
