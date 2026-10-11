//! Platform details of the audio devices.
//!
//! On Linux the ALSA library prints its own diagnostics straight to stderr
//! (for example "cannot find card '0'" on a machine without a sound card).
//! Inside a terminal interface those lines land on top of the rendered frame,
//! so they are silenced once, before the first device is touched.

#[cfg(target_os = "linux")]
mod silence {
    use std::ffi::{c_char, c_int};
    use std::sync::Once;

    unsafe extern "C" fn ignore_message(
        _file: *const c_char,
        _line: c_int,
        _function: *const c_char,
        _error: c_int,
        _format: *const c_char,
    ) {
    }

    pub fn silence_library_messages() {
        static INSTALL: Once = Once::new();
        INSTALL.call_once(|| {
            // SAFETY: ALSA calls the handler with five fixed arguments followed
            // by variadic ones. On the C calling conventions of every Linux
            // target the fixed arguments are passed the same way for variadic
            // and non-variadic functions, so a handler that reads only the
            // fixed arguments (and here reads none) is sound to install.
            let handler: unsafe extern "C" fn(
                *const c_char,
                c_int,
                *const c_char,
                c_int,
                *const c_char,
                ...
            ) = unsafe {
                std::mem::transmute::<
                    unsafe extern "C" fn(*const c_char, c_int, *const c_char, c_int, *const c_char),
                    unsafe extern "C" fn(
                        *const c_char,
                        c_int,
                        *const c_char,
                        c_int,
                        *const c_char,
                        ...
                    ),
                >(ignore_message)
            };
            // SAFETY: installing a process-wide handler has no other
            // preconditions; the function lives for the whole program.
            unsafe {
                alsa_sys::snd_lib_error_set_handler(Some(handler));
            }
        });
    }
}

#[cfg(not(target_os = "linux"))]
mod silence {
    pub fn silence_library_messages() {}
}

pub use silence::silence_library_messages;
