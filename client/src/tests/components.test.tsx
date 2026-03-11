import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { act } from 'react';
import App from '../App';
import ChatInterface from '../components/ChatInterface';
import FileUploadArea from '../components/FileUploadArea';

describe('App Component', () => {
  it('renders without crashing', () => {
    render(<App />);
    expect(screen.getByText(/AI Assistant/i)).toBeInTheDocument();
  });

  it('renders Dashboard content as its child', () => {
    render(<App />);
    expect(screen.getByText(/AI Assistant/i)).toBeInTheDocument();
  });
});

describe('Dashboard (App) Component', () => {
  it('shows AI Assistant title in sidebar', () => {
    render(<App />);
    expect(screen.getByText('AI Assistant')).toBeInTheDocument();
  });

  it('renders both nav buttons', () => {
    render(<App />);
    expect(screen.getByText('Chat Assistant')).toBeInTheDocument();
    expect(screen.getByText('Knowledge Base')).toBeInTheDocument();
  });

  it('has ChatInterface as default active tab', () => {
    render(<App />);
    expect(screen.getByText(/Hello!/i)).toBeInTheDocument();
  });

  it('switches tabs correctly', async () => {
    render(<App />);
    const user = userEvent.setup();
    
    // Switch to Knowledge Base
    await user.click(screen.getByText('Knowledge Base'));
    expect(screen.getByText('Drag and drop your files here')).toBeInTheDocument();
    
    // Switch back to Chat Assistant
    await user.click(screen.getByText('Chat Assistant'));
    expect(screen.getByText(/Hello!/i)).toBeInTheDocument();
  });

  it('applies active tab styling', async () => {
    render(<App />);
    const chatBtn = screen.getByText('Chat Assistant').closest('button');
    expect(chatBtn?.className).toContain('bg-indigo-50 text-indigo-700 bg-white/10 text-white'); // Depending on exact classes, check for white, indigo, etc. We just check truthy class changes usually.
    // Instead of exact class testing, we will just interact with it
  });
});

describe('ChatInterface Component', () => {
  beforeEach(() => {
    vi.mocked(fetch).mockClear();
    window.HTMLElement.prototype.scrollIntoView = vi.fn();
  });

  describe('Rendering', () => {
    it('shows initial welcome message', () => {
      render(<ChatInterface />);
      expect(screen.getByText(/Hello! I am your AI Developer/i)).toBeInTheDocument();
    });

    it('shows input placeholder', () => {
      render(<ChatInterface />);
      expect(screen.getByPlaceholderText(/Ask me anything/i)).toBeInTheDocument();
    });

    it('renders send button and disclaimer', () => {
      render(<ChatInterface />);
      expect(screen.getByRole('button', { name: '' })).toBeInTheDocument(); // Icon button
      expect(screen.getByText(/AI can make mistakes/i)).toBeInTheDocument();
    });
  });

  describe('Interaction', () => {
    it('disables send button when input is empty', () => {
      render(<ChatInterface />);
      const btn = screen.getByRole('button');
      expect(btn).toBeDisabled();
    });

    it('enables send button and updates input when user types', async () => {
      render(<ChatInterface />);
      const user = userEvent.setup();
      const input = screen.getByPlaceholderText(/Ask me/i);
      
      await user.type(input, 'test question');
      expect(input).toHaveValue('test question');
      expect(screen.getByRole('button')).toBeEnabled();
    });

    it('clears input after message is sent', async () => {
      vi.mocked(fetch).mockResolvedValueOnce(
        new Response(JSON.stringify({ response: 'Testing!' }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      );
      
      render(<ChatInterface />);
      const user = userEvent.setup();
      const input = screen.getByPlaceholderText(/Ask me/i);
      
      await user.type(input, 'test question');
      
      await act(async () => {
        await user.click(screen.getByRole('button'));
      });
      
      await waitFor(() => {
        expect(input).toHaveValue('');
      });
    });
  });

  describe('API Integration', () => {
    it('handles successful API call and shows text and sources', async () => {
      vi.mocked(fetch).mockResolvedValueOnce(
        new Response(JSON.stringify({ 
          response: 'This is the AI answer', 
          sources: [{ file: 'test.pdf' }] 
        }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      );
      
      render(<ChatInterface />);
      const user = userEvent.setup();
      
      await user.type(screen.getByPlaceholderText(/Ask me/i), 'API test');
      await act(async () => {
        await user.click(screen.getByRole('button'));
      });
      
      expect(screen.getByText('API test')).toBeInTheDocument();
      
      await waitFor(() => {
        expect(screen.getByText('This is the AI answer')).toBeInTheDocument();
        expect(screen.getByText('test.pdf')).toBeInTheDocument(); // Source badge
      });
      
      expect(fetch).toHaveBeenCalledWith('/api/chat/', expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: expect.stringContaining('"query":"API test"')
      }));
    });

    it('disables input and shows loading dots while waiting', async () => {
      // Mock fetch to never resolve immediately to test loading state
      let resolveRequest: (value: Response) => void;
      const responsePromise = new Promise((resolve) => {
        resolveRequest = resolve as (value: Response) => void;
      });
      vi.mocked(fetch).mockReturnValueOnce(responsePromise as unknown as Promise<Response>);
      
      render(<ChatInterface />);
      const user = userEvent.setup();
      const input = screen.getByPlaceholderText(/Ask me/i);
      
      await user.type(input, 'loading test');
      await act(async () => {
        await user.click(screen.getByRole('button'));
      });
      
      expect(input).toBeDisabled();
      const loadingElements = document.querySelectorAll('.animate-bounce');
      expect(loadingElements.length).toBeGreaterThan(0);
      
      // Complete the request to clean up
      await act(async () => {
        resolveRequest(new Response(JSON.stringify({ response: 'Done' }), { status: 200 }));
      });
    });

    it('shows error message on network failure', async () => {
      vi.mocked(fetch).mockRejectedValueOnce(new Error('Network disconnected'));
      
      render(<ChatInterface />);
      const user = userEvent.setup();
      
      await user.type(screen.getByPlaceholderText(/Ask me/i), 'Fail test');
      await act(async () => {
        await user.click(screen.getByRole('button'));
      });
      
      await waitFor(() => {
        expect(screen.getByText(/Sorry, I encountered an error/i)).toBeInTheDocument();
      });
    });

    it('shows backend error detail on non-ok response', async () => {
      vi.mocked(fetch).mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: 'Gemini quota exceeded' }), {
          status: 429,
          headers: { 'Content-Type': 'application/json' },
        })
      );
      
      render(<ChatInterface />);
      const user = userEvent.setup();
      
      await user.type(screen.getByPlaceholderText(/Ask me/i), 'Limit test');
      await act(async () => {
        await user.click(screen.getByRole('button'));
      });
      
      await waitFor(() => {
        expect(screen.getByText(/Gemini quota exceeded/i)).toBeInTheDocument();
      });
    });

    it('shows default error when json parsing fails on non-ok response', async () => {
      vi.mocked(fetch).mockResolvedValueOnce(
        new Response("Bad Gateway - HTML Error page completely non json", {
          status: 502,
          headers: { 'Content-Type': 'text/html' },
        })
      );
      
      render(<ChatInterface />);
      const user = userEvent.setup();
      
      await user.type(screen.getByPlaceholderText(/Ask me/i), '502 test');
      await act(async () => {
        await user.click(screen.getByRole('button'));
      });
      
      await waitFor(() => {
        expect(screen.getByText(/An unexpected error occurred. Please try again./i)).toBeInTheDocument();
      });
    });

    it('shows default error when a non-Error object is thrown', async () => {
      vi.mocked(fetch).mockRejectedValueOnce("Just a string throw");
      
      render(<ChatInterface />);
      const user = userEvent.setup();
      
      await user.type(screen.getByPlaceholderText(/Ask me/i), 'String throw test');
      await act(async () => {
        await user.click(screen.getByRole('button'));
      });
      
      await waitFor(() => {
        expect(screen.getByText(/⚠️ An unexpected error occurred./i)).toBeInTheDocument();
      });
    });
  });
});

describe('FileUploadArea Component', () => {
  beforeEach(() => {
    vi.mocked(fetch).mockClear();
  });

  describe('Rendering', () => {
    it('shows all required initial elements', () => {
      render(<FileUploadArea />);
      expect(screen.getByText('Knowledge Base')).toBeInTheDocument();
      expect(screen.getByText(/Drag and drop your files here/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Browse Files/i })).toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /Process File/i })).not.toBeInTheDocument();
    });
  });

  describe('File Selection', () => {
    it('shows file info and Process button when selected', async () => {
      render(<FileUploadArea />);
      const user = userEvent.setup();
      
      // Create fake file
      const file = new File(['hello'], 'hello.txt', { type: 'text/plain' });
      // The input might be hidden visually, test by label or input type
      const input = document.querySelector('input[type="file"]') as HTMLInputElement;
      
      await user.upload(input, file);
      
      expect(screen.getByText('hello.txt')).toBeInTheDocument();
      expect(screen.getByText(/0.00 MB/i)).toBeInTheDocument(); // since it's only 5 bytes
      expect(screen.getByRole('button', { name: /Process File/i })).toBeInTheDocument();
    });
  });

  describe('Upload Flow', () => {
    it('handles successful upload', async () => {
      vi.mocked(fetch).mockResolvedValueOnce(
        new Response(JSON.stringify({ message: 'Success' }), {
          status: 200,
        })
      );
      
      render(<FileUploadArea />);
      const user = userEvent.setup();
      const file = new File(['hello'], 'test.txt', { type: 'text/plain' });
      const input = document.querySelector('input[type="file"]') as HTMLInputElement;
      
      await user.upload(input, file);
      await act(async () => {
        await user.click(screen.getByRole('button', { name: /Process File/i }));
      });
      
      expect(fetch).toHaveBeenCalledWith('/api/upload/', expect.objectContaining({
        method: 'POST',
      }));
      
      await waitFor(() => {
        expect(screen.getByText('Success')).toBeInTheDocument();
      });
      // Test success styling/class if needed, or if it renders a specific msg block
    });

    it('shows error on failed response', async () => {
      vi.mocked(fetch).mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: 'Unsupported format' }), {
          status: 400,
        })
      );
      
      render(<FileUploadArea />);
      const user = userEvent.setup();
      const file = new File(['hello'], 'test.exe', { type: 'application/x-msdownload' });
      const input = document.querySelector('input[type="file"]') as HTMLInputElement;
      
      await user.upload(input, file);
      await act(async () => {
        await user.click(screen.getByRole('button', { name: /Process File/i }));
      });
      
      await waitFor(() => {
        expect(screen.getByText(/Unsupported format/i)).toBeInTheDocument();
      });
    });

    it('shows network error correctly', async () => {
      vi.mocked(fetch).mockRejectedValueOnce(new Error('Network Down'));
      
      render(<FileUploadArea />);
      const user = userEvent.setup();
      const file = new File(['hello'], 'test.txt', { type: 'text/plain' });
      const input = document.querySelector('input[type="file"]') as HTMLInputElement;
      
      await user.upload(input, file);
      await act(async () => {
        await user.click(screen.getByRole('button', { name: /Process File/i }));
      });
      
      await waitFor(() => {
        expect(screen.getByText(/Network error occurred/i)).toBeInTheDocument();
      });
    });

    it('shows "Uploading..." text during upload', async () => {
      let resolveRequest: (value: Response) => void;
      const responsePromise = new Promise((resolve) => {
        resolveRequest = resolve as (value: Response) => void;
      });
      vi.mocked(fetch).mockReturnValueOnce(responsePromise as unknown as Promise<Response>);
      
      render(<FileUploadArea />);
      const user = userEvent.setup();
      const file = new File(['hello'], 'test.txt', { type: 'text/plain' });
      const input = document.querySelector('input[type="file"]') as HTMLInputElement;
      
      await user.upload(input, file);
      await act(async () => {
        await user.click(screen.getByRole('button', { name: /Process File/i }));
      });
      
      expect(screen.getByText(/Uploading.../i)).toBeInTheDocument();
      
      await act(async () => {
        resolveRequest(new Response(JSON.stringify({ message: 'Done' }), { status: 200 }));
      });
    });
  });

  describe('Drag and Drop', () => {
    it('handles dragOver without throwing', () => {
      render(<FileUploadArea />);
      const dropZone = screen.getByText(/Drag and drop your files here/i).closest('div');
      
      expect(() => {
        fireEvent.dragOver(dropZone!);
      }).not.toThrow();
    });
    
    it('processes dropped files correctly', () => {
      render(<FileUploadArea />);
      const dropZone = screen.getByText(/Drag and drop your files here/i).closest('div');
      
      const file = new File(['dropped'], 'dragtest.txt', { type: 'text/plain' });
      fireEvent.drop(dropZone!, {
        dataTransfer: {
          files: [file],
        },
      });
      
      expect(screen.getByText('dragtest.txt')).toBeInTheDocument();
    });

    it('ignores empty drop seamlessly', () => {
      render(<FileUploadArea />);
      const dropZone = screen.getByText(/Drag and drop your files here/i).closest('div');
      
      fireEvent.drop(dropZone!, {
        dataTransfer: {
          files: [],
        },
      });
      
      expect(screen.queryByText('dragtest.txt')).not.toBeInTheDocument();
    });
  });
});
