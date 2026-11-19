/* SPIDriver Linux GUI (GTK4 port of c/win32gui).
 *
 * Same dialog as the Win32 utility: device combo, status readout, MISO/MOSI
 * hex logs, CS/A/B checkboxes and a hex-byte transfer box.  Reuses the
 * portable c/common/spidriver.c (POSIX termios path).
 */
#include <dirent.h>
#include <glob.h>
#include <gtk/gtk.h>
#include <stdio.h>
#include <string.h>
#include <sys/select.h>
#include <time.h>
#include <unistd.h>

#include "spidriver.h"

static SPIDriver sd;

static GtkWidget *combo;
static GtkStringList *combo_list;
static GtkWidget *lbl_serial, *lbl_v, *lbl_c, *lbl_t, *lbl_u;
static GtkWidget *chk_a, *chk_b, *chk_cs;
static GtkWidget *edit_tx;
static GtkTextBuffer *buf_miso, *buf_mosi;
static GtkTextView *view_miso, *view_mosi;

static char miso[4096], mosi[4096];

/* signal handlers (defined below, used by is_connected/update_cb) */
static void on_a(GtkToggleButton *b, gpointer data);
static void on_b(GtkToggleButton *b, gpointer data);
static void on_cs(GtkToggleButton *b, gpointer data);
static void on_tx_insert(GtkEditable *e, const char *text, int len, int *pos,
                         gpointer data);
static void on_combo_changed(GtkDropDown *d, gpointer data);

/* ---- small helpers ------------------------------------------------------ */

static void set_label(GtkWidget *lbl, const char *fmt, ...) {
    char buf[80];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);
    gtk_label_set_text(GTK_LABEL(lbl), buf);
}

static void log_scroll(GtkTextView *view) {
    GtkTextBuffer *b = gtk_text_view_get_buffer(view);
    gtk_text_view_scroll_mark_onscreen(view, gtk_text_buffer_get_insert(b));
}

/* ---- device state ------------------------------------------------------- */

static void is_disconnected(void) {
    gtk_widget_set_sensitive(chk_a, FALSE);
    gtk_widget_set_sensitive(chk_b, FALSE);
    gtk_widget_set_sensitive(chk_cs, FALSE);
    gtk_widget_set_sensitive(edit_tx, FALSE);
}

static void is_connected(void) {
    gtk_widget_set_sensitive(chk_a, TRUE);
    gtk_widget_set_sensitive(chk_b, TRUE);
    gtk_widget_set_sensitive(chk_cs, TRUE);
    gtk_widget_set_sensitive(edit_tx, TRUE);

    /* programmatic sync: no command round-trips */
    g_signal_handlers_block_by_func(chk_a, G_CALLBACK(on_a), NULL);
    g_signal_handlers_block_by_func(chk_b, G_CALLBACK(on_b), NULL);
    g_signal_handlers_block_by_func(chk_cs, G_CALLBACK(on_cs), NULL);
    gtk_check_button_set_active(GTK_CHECK_BUTTON(chk_a), sd.a);
    gtk_check_button_set_active(GTK_CHECK_BUTTON(chk_b), sd.b);
    gtk_check_button_set_active(GTK_CHECK_BUTTON(chk_cs), !sd.cs);
    g_signal_handlers_unblock_by_func(chk_a, G_CALLBACK(on_a), NULL);
    g_signal_handlers_unblock_by_func(chk_b, G_CALLBACK(on_b), NULL);
    g_signal_handlers_unblock_by_func(chk_cs, G_CALLBACK(on_cs), NULL);
}

/* bounded status read: returns 1 if the device answered with a
 * SPIDriver status line (starts '[', contains "spidriver") */
static int probe_status(SPIDriver *sd) {
    char buf[100];
    int n = 0;
    time_t deadline = time(NULL) + 1;

    write(sd->port, "?", 1);
    while (n < 80 && time(NULL) < deadline) {
        fd_set fds;
        FD_ZERO(&fds);
        FD_SET(sd->port, &fds);
        struct timeval tv = {0, 200000};
        int r = select(sd->port + 1, &fds, NULL, NULL, &tv);
        if (r <= 0) continue;
        int k = (int)read(sd->port, buf + n, (size_t)(80 - n));
        if (k <= 0) break;
        n += k;
    }
    buf[n] = 0;
    return (n >= 60 && buf[0] == '[' && strstr(buf, "spidriver") != NULL);
}

static void newdevice(void) {
    /* try every listed port until the SPIDriver handshake succeeds */
    guint n = g_list_model_get_n_items(G_LIST_MODEL(combo_list));
    for (guint i = 0; i < n; i++) {
        GObject *item =
            g_list_model_get_item(G_LIST_MODEL(combo_list), i);
        const char *dev =
            gtk_string_object_get_string(GTK_STRING_OBJECT(item));
        spi_connect(&sd, dev);
        g_object_unref(item);
        if (sd.connected && probe_status(&sd)) {
            g_signal_handlers_block_by_func(combo, G_CALLBACK(on_combo_changed),
                                            NULL);
            gtk_drop_down_set_selected(GTK_DROP_DOWN(combo), i);
            g_signal_handlers_unblock_by_func(
                combo, G_CALLBACK(on_combo_changed), NULL);
            is_connected();
            return;
        }
        /* wrong device (or no status): drop it and try the next port */
        close(sd.port);
        sd.connected = 0;
    }
    is_disconnected();
}

static void scan_ports(void) {
    guint n = g_list_model_get_n_items(G_LIST_MODEL(combo_list));
    gtk_string_list_splice(combo_list, 0, n, NULL);

    /* CDC ports first (the Pico enumerates as ttyACM), then FTDI-style
     * ttyUSB (the original SPIDriver), then plain serial ports */
    const char *patterns[] = {"/dev/ttyACM*", "/dev/ttyUSB*", "/dev/ttyS*"};
    for (unsigned i = 0; i < sizeof(patterns) / sizeof(patterns[0]); i++) {
        glob_t g;
        if (glob(patterns[i], 0, NULL, &g) == 0) {
            for (unsigned j = 0; j < g.gl_pathc; j++) {
                gtk_string_list_append(combo_list, g.gl_pathv[j]);
            }
        }
        globfree(&g);
    }

    /* stable by-id names last (symlinks into the above; the probe walks
     * the list in order, so ttyACM candidates are tried first) */
    DIR *d = opendir("/dev/serial/by-id");
    if (d) {
        struct dirent *de;
        while ((de = readdir(d))) {
            if (de->d_name[0] == '.') continue;
            char path[512];
            snprintf(path, sizeof(path), "/dev/serial/by-id/%s", de->d_name);
            gtk_string_list_append(combo_list, path);
        }
        closedir(d);
    }

    if (gtk_drop_down_get_selected(GTK_DROP_DOWN(combo)) ==
        GTK_INVALID_LIST_POSITION) {
        gtk_drop_down_set_selected(GTK_DROP_DOWN(combo), 0);
    }
}

static gboolean update_cb(gpointer data) {
    (void)data;
    if (sd.connected) {
        spi_getstatus(&sd);
        set_label(lbl_serial, "%s", sd.serial);
        set_label(lbl_v, "%.2f V", sd.voltage_v);
        set_label(lbl_c, "%.0f mA", sd.current_ma);
        set_label(lbl_t, "%.1f C", sd.temp_celsius);
        unsigned days = (unsigned)(sd.uptime / (24 * 3600));
        unsigned rem = (unsigned)(sd.uptime % (24 * 3600));
        unsigned hh = rem / 3600, mm = (rem / 60) % 60, ss = rem % 60;
        set_label(lbl_u, "%d:%02d:%02d:%02d", days, hh, mm, ss);

        /* keep CS/A/B checkboxes in sync with the device state */
        g_signal_handlers_block_by_func(chk_a, G_CALLBACK(on_a), NULL);
        g_signal_handlers_block_by_func(chk_b, G_CALLBACK(on_b), NULL);
        g_signal_handlers_block_by_func(chk_cs, G_CALLBACK(on_cs), NULL);
        gtk_check_button_set_active(GTK_CHECK_BUTTON(chk_a), sd.a);
        gtk_check_button_set_active(GTK_CHECK_BUTTON(chk_b), sd.b);
        gtk_check_button_set_active(GTK_CHECK_BUTTON(chk_cs), !sd.cs);
        g_signal_handlers_unblock_by_func(chk_a, G_CALLBACK(on_a), NULL);
        g_signal_handlers_unblock_by_func(chk_b, G_CALLBACK(on_b), NULL);
        g_signal_handlers_unblock_by_func(chk_cs, G_CALLBACK(on_cs), NULL);
    }
    return G_SOURCE_CONTINUE;
}

/* ---- signal handlers ---------------------------------------------------- */

static void on_combo_changed(GtkDropDown *c, gpointer data) {
    (void)c;
    (void)data;
    newdevice();
}

static void on_a(GtkToggleButton *b, gpointer data) {
    (void)data;
    if (sd.connected) {
        spi_seta(&sd, gtk_check_button_get_active(GTK_CHECK_BUTTON(b)));
    }
}

static void on_b(GtkToggleButton *b, gpointer data) {
    (void)data;
    if (sd.connected) {
        spi_setb(&sd, gtk_check_button_get_active(GTK_CHECK_BUTTON(b)));
    }
}

static void on_cs(GtkToggleButton *b, gpointer data) {
    (void)data;
    if (sd.connected) {
        if (gtk_check_button_get_active(GTK_CHECK_BUTTON(b))) {
            spi_sel(&sd);
        } else {
            spi_unsel(&sd);
        }
    }
}

/* hex-byte filter: only hex digits (both cases) and spaces; anything else
 * is not inserted.  No revert/rewrite games, so no feedback loops. */
static void on_tx_insert(GtkEditable *ed, const char *text, int len, int *pos,
                         gpointer data) {
    (void)pos;
    (void)data;
    for (int i = 0; i < len; i++) {
        if (strchr("0123456789abcdefABCDEF ", text[i]) == NULL) {
            g_signal_stop_emission_by_name(ed, "insert-text");
            return;
        }
    }
}

static void on_transfer(GtkButton *b, gpointer data) {
    (void)b;
    (void)data;
    if (!sd.connected) return;

    const char *t = gtk_editable_get_text(GTK_EDITABLE(edit_tx));
    if (!*t) return;

    /* parse a hex byte string: "DE AD BE EF" -> 4 bytes (no 0x prefix) */
    char send[256], tx_log[1024];
    int n = 0, hi = -1;
    for (const char *p = t; *p; p++) {
        if (*p == ' ') continue;
        int v;
        if (*p >= '0' && *p <= '9') {
            v = *p - '0';
        } else {
            char c = (*p >= 'a' && *p <= 'f') ? (char)(*p - 32) : *p;
            v = c - 'A' + 10;
        }
        if (hi < 0) {
            hi = v;
        } else {
            send[n++] = (char)((hi << 4) | v);
            hi = -1;
        }
    }
    if (hi >= 0) send[n++] = (char)hi; /* lone trailing nibble */
    if (n == 0) return;

    memcpy(tx_log, send, (size_t)n);
    spi_writeread(&sd, send, (size_t)n);

    gtk_editable_set_text(GTK_EDITABLE(edit_tx), "");

    for (int i = 0; i < n; i++) {
        sprintf(mosi + strlen(mosi), "%02x ", tx_log[i] & 0xff);
        sprintf(miso + strlen(miso), "%02x ", send[i] & 0xff);
    }

    gtk_text_buffer_set_text(buf_miso, miso, -1);
    log_scroll(view_miso);
    gtk_text_buffer_set_text(buf_mosi, mosi, -1);
    log_scroll(view_mosi);
}

/* ---- layout ------------------------------------------------------------- */

static GtkWidget *make_readout(void) {
    GtkWidget *grid = gtk_grid_new();
    gtk_grid_set_column_spacing(GTK_GRID(grid), 10);
    gtk_grid_set_row_spacing(GTK_GRID(grid), 4);

    struct {
        const char *name;
        GtkWidget **lbl;
    } rows[] = {
        {"Serial", &lbl_serial}, {"Voltage", &lbl_v}, {"Current", &lbl_c},
        {"Temp.", &lbl_t},       {"Running", &lbl_u},
    };
    for (unsigned i = 0; i < sizeof(rows) / sizeof(rows[0]); i++) {
        GtkWidget *name = gtk_label_new(rows[i].name);
        gtk_widget_set_halign(name, GTK_ALIGN_START);
        *rows[i].lbl = gtk_label_new("-");
        gtk_label_set_xalign(GTK_LABEL(*rows[i].lbl), 1.0);
        gtk_widget_set_halign(*rows[i].lbl, GTK_ALIGN_END);
        gtk_grid_attach(GTK_GRID(grid), name, 0, (int)i, 1, 1);
        gtk_grid_attach(GTK_GRID(grid), *rows[i].lbl, 1, (int)i, 1, 1);
    }
    return grid;
}

static GtkWidget *make_log(GtkTextView **view, GtkTextBuffer **buf) {
    *buf = gtk_text_buffer_new(NULL);
    *view = GTK_TEXT_VIEW(gtk_text_view_new_with_buffer(*buf));
    gtk_text_view_set_editable(*view, FALSE);
    gtk_text_view_set_cursor_visible(*view, FALSE);
    gtk_text_view_set_justification(*view, GTK_JUSTIFY_RIGHT);
    gtk_text_view_set_wrap_mode(*view, GTK_WRAP_NONE);
    gtk_widget_set_size_request(GTK_WIDGET(*view), 220, -1);
    return GTK_WIDGET(*view);
}

static void activate(GtkApplication *app, gpointer data) {
    (void)data;
    GtkWidget *win = gtk_application_window_new(app);
    gtk_window_set_title(GTK_WINDOW(win), "SPIDriver");
    gtk_window_set_default_size(GTK_WINDOW(win), 340, 420);

    combo = gtk_drop_down_new(NULL, NULL);
    combo_list = gtk_string_list_new(NULL);
    gtk_drop_down_set_model(GTK_DROP_DOWN(combo), G_LIST_MODEL(combo_list));
    scan_ports();
    g_signal_connect(combo, "notify::selected", G_CALLBACK(on_combo_changed),
                     NULL);

    chk_cs = gtk_check_button_new_with_label("CS");
    chk_a = gtk_check_button_new_with_label("A");
    chk_b = gtk_check_button_new_with_label("B");
    g_signal_connect(chk_a, "toggled", G_CALLBACK(on_a), NULL);
    g_signal_connect(chk_b, "toggled", G_CALLBACK(on_b), NULL);
    g_signal_connect(chk_cs, "toggled", G_CALLBACK(on_cs), NULL);

    GtkWidget *check_row = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 12);
    gtk_box_append(GTK_BOX(check_row), chk_cs);
    gtk_box_append(GTK_BOX(check_row), chk_a);
    gtk_box_append(GTK_BOX(check_row), chk_b);

    edit_tx = gtk_entry_new();
    gtk_entry_set_max_length(GTK_ENTRY(edit_tx), 160);
    g_signal_connect(edit_tx, "insert-text", G_CALLBACK(on_tx_insert), NULL);
    g_signal_connect(edit_tx, "activate", G_CALLBACK(on_transfer), NULL);

    GtkWidget *btn_tx = gtk_button_new_with_label("Transfer");
    g_signal_connect(btn_tx, "clicked", G_CALLBACK(on_transfer), NULL);

    GtkWidget *tx_row = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    gtk_box_append(GTK_BOX(tx_row), edit_tx);
    gtk_box_append(GTK_BOX(tx_row), btn_tx);

    GtkWidget *grid = gtk_grid_new();
    gtk_grid_set_column_spacing(GTK_GRID(grid), 8);
    gtk_grid_set_row_spacing(GTK_GRID(grid), 6);
    gtk_widget_set_margin_start(grid, 10);
    gtk_widget_set_margin_end(grid, 10);
    gtk_widget_set_margin_top(grid, 10);
    gtk_widget_set_margin_bottom(grid, 10);

    int row = 0;
    gtk_grid_attach(GTK_GRID(grid), combo, 0, row++, 2, 1);
    gtk_grid_attach(GTK_GRID(grid), make_readout(), 0, row++, 2, 1);

    gtk_grid_attach(GTK_GRID(grid), gtk_label_new("MISO"), 0, row, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), make_log(&view_miso, &buf_miso), 1, row++,
                    1, 1);
    gtk_grid_attach(GTK_GRID(grid), gtk_label_new("MOSI"), 0, row, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), make_log(&view_mosi, &buf_mosi), 1, row++,
                    1, 1);

    gtk_grid_attach(GTK_GRID(grid), check_row, 0, row++, 2, 1);
    gtk_grid_attach(GTK_GRID(grid), tx_row, 0, row++, 2, 1);

    gtk_window_set_child(GTK_WINDOW(win), grid);

    /* monospace for the hex logs */
    GtkCssProvider *css = gtk_css_provider_new();
    gtk_css_provider_load_from_string(
        css, "textview { font-family: monospace; }");
    gtk_style_context_add_provider_for_display(
        gtk_widget_get_display(win), GTK_STYLE_PROVIDER(css),
        GTK_STYLE_PROVIDER_PRIORITY_APPLICATION);
    g_object_unref(css);

    newdevice();
    g_timeout_add(1000, update_cb, NULL);

    gtk_window_present(GTK_WINDOW(win));
}

int main(int argc, char **argv) {
    GtkApplication *app =
        gtk_application_new("com.excamera.spidriver", G_APPLICATION_DEFAULT_FLAGS);
    g_signal_connect(app, "activate", G_CALLBACK(activate), NULL);
    int status = g_application_run(G_APPLICATION(app), argc, argv);
    g_object_unref(app);
    return status;
}
