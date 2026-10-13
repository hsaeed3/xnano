//! Keeping text written to standard output and standard error off the screen of a live
//! session.
//!
//! A live session draws with escape sequences on the terminal. Anything else written to the
//! terminal at the same time (a `print`, a log record, a warning, a message from a native
//! library) lands in the middle of a frame and corrupts the display. While a session is open,
//! [`OutputCapture`] points descriptors 1 and 2 at pipes and reads them on background
//! threads, so nothing a program prints can reach the screen. The session itself draws
//! through [`terminal_output`], which keeps writing to the real terminal. When the session
//! ends, whatever was not collected with [`OutputCapture::take`] is printed to the stream it
//! was written to, so no output is lost.
//!
//! On platforms other than Unix nothing is captured.

use std::collections::VecDeque;
use std::io::{self, IsTerminal, Write};
#[cfg(unix)]
use std::sync::atomic::AtomicBool;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{Arc, Mutex};

/// The most captured bytes kept; older output is dropped first.
pub const MAXIMUM_CAPTURED_BYTES: usize = 8 * 1024 * 1024;

/// Which stream a chunk was written to.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Stream {
    Output,
    Error,
}

#[derive(Debug)]
struct Chunk {
    sequence: u64,
    stream: Stream,
    bytes: Vec<u8>,
}

/// Called from a background thread whenever new output was captured.
pub type OutputNotifier = Arc<dyn Fn() + Send + Sync>;

// Output is only captured on Unix, so nothing is pushed elsewhere.
#[cfg_attr(not(unix), allow(dead_code))]
#[derive(Default)]
struct Captured {
    chunks: Mutex<VecDeque<Chunk>>,
    total_bytes: Mutex<usize>,
    dropped_bytes: AtomicU64,
    next_sequence: AtomicU64,
}

#[cfg_attr(not(unix), allow(dead_code))]
impl Captured {
    fn push(&self, stream: Stream, bytes: &[u8]) {
        let mut chunks = self
            .chunks
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        let mut total = self
            .total_bytes
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        chunks.push_back(Chunk {
            sequence: self.next_sequence.fetch_add(1, Ordering::SeqCst),
            stream,
            bytes: bytes.to_vec(),
        });
        *total += bytes.len();
        while *total > MAXIMUM_CAPTURED_BYTES {
            let Some(oldest) = chunks.pop_front() else {
                break;
            };
            *total -= oldest.bytes.len();
            self.dropped_bytes
                .fetch_add(oldest.bytes.len() as u64, Ordering::SeqCst);
        }
    }

    fn drain(&self) -> Vec<Chunk> {
        let mut chunks = self
            .chunks
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        *self
            .total_bytes
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner) = 0;
        std::mem::take(&mut *chunks).into()
    }
}

#[cfg(unix)]
mod platform {
    use std::fs::File;
    use std::io::{self, Read};
    use std::os::fd::OwnedFd;
    use std::sync::Mutex;
    use std::sync::atomic::Ordering;
    use std::thread::JoinHandle;
    use std::time::Duration;

    use rustix::event::{PollFd, PollFlags, Timespec, poll};
    use rustix::io::dup;
    use rustix::pipe::pipe;
    use rustix::stdio::{dup2_stderr, dup2_stdout, stderr, stdout};

    use super::{Arc, AtomicBool, Captured, OutputNotifier, Stream};

    /// The real terminal, while output is captured.
    pub static REAL_TERMINAL: Mutex<Option<Arc<File>>> = Mutex::new(None);

    /// The descriptors needed to point standard output at the terminal and back.
    struct Lift {
        real_output: OwnedFd,
        captured_output: OwnedFd,
    }

    static LIFT: Mutex<Option<Arc<Lift>>> = Mutex::new(None);

    pub struct Redirect {
        real_output: OwnedFd,
        real_error: OwnedFd,
        should_stop: Arc<AtomicBool>,
        readers: Vec<JoinHandle<()>>,
    }

    /// Standard output points at the real terminal for as long as this lives.
    pub struct LiftGuard(Option<Arc<Lift>>);

    impl Drop for LiftGuard {
        fn drop(&mut self) {
            if let Some(lift) = &self.0 {
                let _ = dup2_stdout(&lift.captured_output);
            }
        }
    }

    pub fn lift() -> LiftGuard {
        let lift = LIFT
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner)
            .clone();
        if let Some(lift) = &lift {
            let _ = dup2_stdout(&lift.real_output);
        }
        LiftGuard(lift)
    }

    fn read_loop(
        pipe: File,
        stream: Stream,
        captured: &Captured,
        should_stop: &AtomicBool,
        notifier: Option<&OutputNotifier>,
    ) {
        let mut pipe = pipe;
        let mut buffer = vec![0_u8; 16 * 1024];
        loop {
            let timeout = Timespec {
                tv_sec: 0,
                tv_nsec: Duration::from_millis(40).as_nanos() as _,
            };
            let is_readable = {
                let mut descriptors = [PollFd::new(&pipe, PollFlags::IN)];
                matches!(poll(&mut descriptors, Some(&timeout)), Ok(count) if count > 0)
            };
            if !is_readable {
                if should_stop.load(Ordering::SeqCst) {
                    return;
                }
                continue;
            }
            match pipe.read(&mut buffer) {
                // Every writer closed.
                Ok(0) => return,
                Ok(count) => {
                    captured.push(stream, &buffer[..count]);
                    if let Some(notify) = notifier {
                        notify();
                    }
                }
                Err(error) if error.kind() == io::ErrorKind::Interrupted => {}
                Err(_) => return,
            }
        }
    }

    pub fn start(
        captured: &Arc<Captured>,
        notifier: Option<OutputNotifier>,
    ) -> io::Result<Redirect> {
        let real_output = dup(stdout())?;
        let real_error = dup(stderr())?;
        let (output_read, output_write) = pipe()?;
        let (error_read, error_write) = pipe()?;
        dup2_stdout(&output_write)?;
        dup2_stderr(&error_write)?;
        // Only descriptors 1 and 2 (and the lift below) may keep the write ends open, so
        // the readers see the end of the stream when they are restored.
        drop(error_write);
        *LIFT
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner) = Some(Arc::new(Lift {
            real_output: real_output.try_clone()?,
            captured_output: output_write,
        }));
        *REAL_TERMINAL
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner) =
            Some(Arc::new(File::from(real_output.try_clone()?)));
        let should_stop = Arc::new(AtomicBool::new(false));
        let mut readers = Vec::new();
        for (read_end, stream) in [(output_read, Stream::Output), (error_read, Stream::Error)] {
            let captured = Arc::clone(captured);
            let should_stop = Arc::clone(&should_stop);
            let notifier = notifier.clone();
            readers.push(
                std::thread::Builder::new()
                    .name("xnano-output-capture".into())
                    .spawn(move || {
                        read_loop(
                            File::from(read_end),
                            stream,
                            &captured,
                            &should_stop,
                            notifier.as_ref(),
                        );
                    })?,
            );
        }
        Ok(Redirect {
            real_output,
            real_error,
            should_stop,
            readers,
        })
    }

    impl Redirect {
        /// Point descriptors 1 and 2 back at the terminal and stop the readers once they
        /// have read everything that was written.
        pub fn restore(self) {
            let _ = dup2_stdout(&self.real_output);
            let _ = dup2_stderr(&self.real_error);
            *REAL_TERMINAL
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner) = None;
            *LIFT
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner) = None;
            self.should_stop.store(true, Ordering::SeqCst);
            for reader in self.readers {
                let _ = reader.join();
            }
        }
    }

    pub fn real_terminal() -> Option<Arc<File>> {
        REAL_TERMINAL
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner)
            .clone()
    }
}

#[cfg(not(unix))]
mod platform {
    use std::io;
    use std::sync::Arc;

    use super::{Captured, OutputNotifier};

    pub struct Redirect;

    pub struct LiftGuard;

    impl Drop for LiftGuard {
        fn drop(&mut self) {}
    }

    pub fn lift() -> LiftGuard {
        LiftGuard
    }

    pub fn start(
        _captured: &Arc<Captured>,
        _notifier: Option<OutputNotifier>,
    ) -> io::Result<Redirect> {
        Err(io::Error::new(
            io::ErrorKind::Unsupported,
            "output capture is not available on this platform",
        ))
    }

    impl Redirect {
        pub fn restore(self) {}
    }
}

/// Point standard output at the real terminal until the guard is dropped.
///
/// Some terminal libraries write their questions (such as "where is the cursor?") to
/// standard output without being given a writer. While output is captured those would
/// land in the capture, so they are asked with this held.
pub fn lift_capture() -> impl Drop {
    platform::lift()
}

/// Where the live session draws: the real terminal, even while output is captured.
pub struct TerminalOutput(OutputTarget);

enum OutputTarget {
    Standard(io::Stdout),
    #[cfg(unix)]
    Terminal(io::BufWriter<std::fs::File>),
}

/// A writer for the real terminal.
///
/// While output is captured this is a buffered copy of the descriptor that was standard
/// output when capturing started; otherwise it is standard output.
pub fn terminal_output() -> TerminalOutput {
    #[cfg(unix)]
    if let Some(terminal) = platform::real_terminal()
        && let Ok(file) = terminal.try_clone()
    {
        return TerminalOutput(OutputTarget::Terminal(io::BufWriter::with_capacity(
            64 * 1024,
            file,
        )));
    }
    TerminalOutput(OutputTarget::Standard(io::stdout()))
}

impl TerminalOutput {
    /// Whether this writes to a terminal.
    pub fn is_terminal(&self) -> bool {
        match &self.0 {
            OutputTarget::Standard(output) => output.is_terminal(),
            #[cfg(unix)]
            OutputTarget::Terminal(output) => output.get_ref().is_terminal(),
        }
    }
}

/// The descriptor that was standard output when capturing started, while it is captured.
///
/// Used to ask what the terminal supports while standard output is a pipe.
pub fn real_terminal_file() -> Option<Arc<std::fs::File>> {
    #[cfg(unix)]
    {
        platform::real_terminal()
    }
    #[cfg(not(unix))]
    {
        None
    }
}

impl Write for TerminalOutput {
    fn write(&mut self, bytes: &[u8]) -> io::Result<usize> {
        match &mut self.0 {
            OutputTarget::Standard(output) => output.write(bytes),
            #[cfg(unix)]
            OutputTarget::Terminal(output) => output.write(bytes),
        }
    }

    fn flush(&mut self) -> io::Result<()> {
        match &mut self.0 {
            OutputTarget::Standard(output) => output.flush(),
            #[cfg(unix)]
            OutputTarget::Terminal(output) => output.flush(),
        }
    }
}

/// Standard output and standard error, captured until [`OutputCapture::finish`].
pub struct OutputCapture {
    captured: Arc<Captured>,
    redirect: Option<platform::Redirect>,
}

impl OutputCapture {
    /// Start capturing. `notifier` is called from a background thread when output arrives.
    ///
    /// Anything the program has buffered itself (Python's `sys.stdout`, for example) should
    /// be flushed first, so it is shown before the session rather than inside it.
    pub fn start(notifier: Option<OutputNotifier>) -> io::Result<Self> {
        let captured = Arc::new(Captured::default());
        let _ = io::stdout().flush();
        let _ = io::stderr().flush();
        let redirect = platform::start(&captured, notifier)?;
        Ok(Self {
            captured,
            redirect: Some(redirect),
        })
    }

    /// Everything captured since the last call, with both streams joined. Text from one
    /// stream keeps the order it was written in; text from the two streams is joined in the
    /// order it was read, which can differ slightly from the order it was written. The
    /// text is no longer printed when the capture finishes.
    pub fn take(&self) -> String {
        let mut chunks = self.captured.drain();
        chunks.sort_by_key(|chunk| chunk.sequence);
        let bytes: Vec<u8> = chunks.into_iter().flat_map(|chunk| chunk.bytes).collect();
        String::from_utf8_lossy(&bytes).into_owned()
    }

    /// Give standard output and standard error back, then print what was not taken to the
    /// stream it was written to.
    pub fn finish(mut self) {
        self.finish_in_place();
    }

    fn finish_in_place(&mut self) {
        let Some(redirect) = self.redirect.take() else {
            return;
        };
        let _ = io::stdout().flush();
        let _ = io::stderr().flush();
        redirect.restore();
        let mut chunks = self.captured.drain();
        chunks.sort_by_key(|chunk| chunk.sequence);
        let (mut output, mut error) = (io::stdout().lock(), io::stderr().lock());
        for chunk in chunks {
            let _ = match chunk.stream {
                Stream::Output => output.write_all(&chunk.bytes),
                Stream::Error => error.write_all(&chunk.bytes),
            };
        }
        let dropped = self.captured.dropped_bytes.load(Ordering::SeqCst);
        if dropped > 0 {
            let _ = writeln!(
                error,
                "xnano: {dropped} bytes of earlier output were dropped because more than \
                 {MAXIMUM_CAPTURED_BYTES} bytes were written during the live session"
            );
        }
        let _ = output.flush();
        let _ = error.flush();
    }
}

impl Drop for OutputCapture {
    fn drop(&mut self) {
        self.finish_in_place();
    }
}

#[cfg(all(test, unix))]
mod tests {
    use super::*;

    /// Descriptors 1 and 2 are process-wide, so the capture tests run one at a time.
    static SERIAL: Mutex<()> = Mutex::new(());

    #[test]
    fn captured_output_is_taken_and_kept_off_the_terminal() {
        let _serial = SERIAL
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        let capture = OutputCapture::start(None).expect("capture starts");
        // Writes straight to descriptors 1 and 2, as a native library would.
        {
            use std::os::fd::AsFd;
            let _ = rustix::io::write(rustix::stdio::stdout().as_fd(), b"first\n");
            let _ = rustix::io::write(rustix::stdio::stderr().as_fd(), b"second\n");
            let _ = rustix::io::write(rustix::stdio::stdout().as_fd(), b"third\n");
        }
        let mut text = String::new();
        for _ in 0..100 {
            text.push_str(&capture.take());
            if ["first", "second", "third"]
                .iter()
                .all(|word| text.lines().any(|line| line == *word))
            {
                break;
            }
            std::thread::sleep(std::time::Duration::from_millis(20));
        }
        capture.finish();
        // The test harness prints from other threads too, so only these lines are checked.
        let position = |word: &str| text.lines().position(|line| line == word);
        assert!(position("second").is_some());
        // Within one stream the order is the order written.
        assert!(position("first") < position("third"));
        assert!(position("first").is_some());
    }

    #[test]
    fn the_terminal_writer_bypasses_the_capture() {
        let _serial = SERIAL
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        let capture = OutputCapture::start(None).expect("capture starts");
        let mut terminal = terminal_output();
        terminal
            .write_all(b"frame")
            .expect("the real terminal accepts writes");
        terminal.flush().expect("and flushes");
        std::thread::sleep(std::time::Duration::from_millis(100));
        assert!(
            !capture.take().contains("frame"),
            "drawing is not captured output"
        );
        capture.finish();
    }

    #[test]
    fn finishing_restores_the_descriptors() {
        let _serial = SERIAL
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        let capture = OutputCapture::start(None).expect("capture starts");
        capture.finish();
        // After the capture, a writer is the real standard output again.
        assert!(matches!(terminal_output().0, OutputTarget::Standard(_)));
    }

    #[test]
    fn the_oldest_output_is_dropped_past_the_limit() {
        let captured = Captured::default();
        let block = vec![b'x'; MAXIMUM_CAPTURED_BYTES / 2 + 1];
        captured.push(Stream::Output, &block);
        captured.push(Stream::Output, &block);
        assert_eq!(captured.drain().len(), 1);
        assert_eq!(
            captured.dropped_bytes.load(Ordering::SeqCst),
            block.len() as u64
        );
    }
}
