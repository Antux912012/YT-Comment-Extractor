document.addEventListener('DOMContentLoaded', function() {
    const urlInput = document.getElementById('videoUrl');
    const numCommentsSelect = document.getElementById('numComments');
    const searchBtn = document.getElementById('searchBtn');
    const loadingSpinner = document.getElementById('loadingSpinner');
    const errorMessage = document.getElementById('errorMessage');
    const resultsSection = document.getElementById('resultsSection');
    const downloadCsvBtn = document.getElementById('downloadCsvBtn');
    const downloadJsonBtn = document.getElementById('downloadJsonBtn');
    const viewJsonBtn = document.getElementById('viewJsonBtn');
    const copyBtn = document.getElementById('copyBtn');
    const commentsList = document.getElementById('commentsList');
    const commentCount = document.getElementById('commentCount');
    const totalCount = document.getElementById('totalCount');
    const selectionInfo = document.getElementById('selectionInfo');

    let currentComments = [];
    let totalAvailable = 0;
    const themeToggle = document.getElementById('themeToggle');

    if (themeToggle) {
        initTheme();
    }

    // Handle Enter key in input
    urlInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            searchBtn.click();
        }
    });

    // Search button click
    searchBtn.addEventListener('click', async function() {
        const videoUrl = urlInput.value.trim();
        const numComments = numCommentsSelect.value;

        if (!videoUrl) {
            showError('Please enter a YouTube video URL');
            return;
        }

        if (!isValidYoutubeUrl(videoUrl)) {
            showError('Please enter a valid YouTube URL');
            return;
        }

        await extractComments(videoUrl, numComments);
    });

    // CSV Download button click
    downloadCsvBtn.addEventListener('click', function() {
        if (currentComments.length === 0) {
            showError('No comments to download');
            return;
        }
        downloadCSV(currentComments);
    });

    // JSON Download button click
    downloadJsonBtn.addEventListener('click', function() {
        if (currentComments.length === 0) {
            showError('No comments to download');
            return;
        }
        downloadJSON(currentComments);
    });

    // JSON View button click
    viewJsonBtn.addEventListener('click', function() {
        if (currentComments.length === 0) {
            showError('No comments to view');
            return;
        }
        showJsonModal(currentComments);
    });

    // Copy button click
    copyBtn.addEventListener('click', function() {
        if (currentComments.length === 0) {
            showError('No comments to copy');
            return;
        }

        copyToClipboard(currentComments);
    });

    function isValidYoutubeUrl(url) {
        const youtubeRegex = /^(https?:\/\/)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)\//;
        return youtubeRegex.test(url);
    }

    function initTheme() {
        const savedTheme = localStorage.getItem('theme') || 'light';
        applyTheme(savedTheme);

        themeToggle.addEventListener('click', () => {
            const nextTheme = document.body.classList.contains('theme-dark') ? 'light' : 'dark';
            applyTheme(nextTheme);
        });
    }

    function applyTheme(theme) {
        if (theme === 'dark') {
            document.body.classList.add('theme-dark');
            themeToggle.textContent = 'Switch to light mode';
        } else {
            document.body.classList.remove('theme-dark');
            themeToggle.textContent = 'Switch to dark mode';
        }
        localStorage.setItem('theme', theme);
    }

    function showError(message) {
        errorMessage.textContent = message;
        errorMessage.style.display = 'block';
        errorMessage.classList.add('error');
        resultsSection.style.display = 'none';
        loadingSpinner.style.display = 'none';
    }

    function hideError() {
        errorMessage.style.display = 'none';
        errorMessage.classList.remove('error');
    }

    async function extractComments(videoUrl, numComments) {
        loadingSpinner.style.display = 'block';
        resultsSection.style.display = 'none';
        hideError();

        try {
            const response = await fetch('/api/extract', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    url: videoUrl,
                    num_comments: numComments
                })
            });

            const data = await response.json();

            if (!response.ok) {
                showError(data.error || 'Error extracting comments');
                loadingSpinner.style.display = 'none';
                return;
            }

            if (data.success) {
                currentComments = data.comments;
                displayComments(data.comments, data.total_available);
                resultsSection.style.display = 'block';
                hideError();
            } else {
                showError(data.error || 'Error extracting comments');
            }
        } catch (error) {
            console.error('Error:', error);
            showError('Error connecting to server. Make sure the server is running.');
        } finally {
            loadingSpinner.style.display = 'none';
        }
    }

    function displayComments(comments, total) {
        currentComments = comments;
        totalAvailable = total || comments.length;
        
        commentCount.textContent = comments.length;
        totalCount.textContent = totalAvailable;
        
        // Calculate and display selection info
        const percentage = totalAvailable > 0 ? ((comments.length / totalAvailable) * 100).toFixed(1) : 100;
        const selectedInfo = `Selected: ${comments.length} out of ${totalAvailable} total comments (${percentage}%)`;
        selectionInfo.textContent = selectedInfo;
        
        commentsList.innerHTML = '';

        comments.forEach((comment, index) => {
            const row = document.createElement('tr');
            
            // Truncate comment for display
            const truncatedComment = comment.comment.substring(0, 150) + 
                                    (comment.comment.length > 150 ? '...' : '');
            const commentDate = comment.date ? escapeHtml(comment.date) : '-';
            
            row.innerHTML = `
                <td>${escapeHtml(comment.nickname)}</td>
                <td>${commentDate}</td>
                <td title="${escapeHtml(comment.comment)}">
                    <span class="comment-text">${escapeHtml(truncatedComment)}</span>
                </td>
            `;
            commentsList.appendChild(row);
        });
    }

    function downloadCSV(comments) {
        let csvContent = 'Nickname|Date|Comment\n';

        comments.forEach(comment => {
            const nickname = escapeCSV(comment.nickname);
            const date = escapeCSV(comment.date || '');
            const text = escapeCSV(comment.comment);

            csvContent += `${nickname}|${date}|${text}\n`;
        });

        // Create blob and download
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);

        link.setAttribute('href', url);
        link.setAttribute('download', `youtube_comments_${getTimestamp()}.csv`);
        link.style.visibility = 'hidden';

        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    function downloadJSON(comments) {
        const jsonData = {
            metadata: {
                extracted_at: new Date().toISOString(),
                total_comments: comments.length,
                export_format: 'JSON'
            },
            comments: comments
        };

        const jsonContent = JSON.stringify(jsonData, null, 2);
        const blob = new Blob([jsonContent], { type: 'application/json;charset=utf-8;' });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);

        link.setAttribute('href', url);
        link.setAttribute('download', `youtube_comments_${getTimestamp()}.json`);
        link.style.visibility = 'hidden';

        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    function showJsonModal(comments) {
        const jsonData = {
            metadata: {
                extracted_at: new Date().toISOString(),
                total_comments: comments.length
            },
            comments: comments
        };

        const jsonContent = JSON.stringify(jsonData, null, 2);
        const modal = document.createElement('div');
        modal.className = 'json-modal';
        modal.innerHTML = `
            <div class="json-modal-content">
                <div class="json-modal-header">
                    <h3>JSON Preview</h3>
                    <button class="json-modal-close">&times;</button>
                </div>
                <div class="json-modal-body">
                    <pre><code>${escapeHtml(jsonContent)}</code></pre>
                </div>
                <div class="json-modal-footer">
                    <button class="btn btn-copy-json">Copy JSON</button>
                    <button class="json-modal-close-btn">Close</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        modal.classList.add('active');

        const closeBtn = modal.querySelector('.json-modal-close');
        const closeBtnFooter = modal.querySelector('.json-modal-close-btn');
        const copyJsonBtn = modal.querySelector('.btn-copy-json');

        closeBtn.addEventListener('click', () => modal.remove());
        closeBtnFooter.addEventListener('click', () => modal.remove());

        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });

        copyJsonBtn.addEventListener('click', () => {
            navigator.clipboard.writeText(jsonContent);
            copyJsonBtn.textContent = '✓ Copied!';
            setTimeout(() => {
                copyJsonBtn.textContent = 'Copy JSON';
            }, 2000);
        });
    }

    function copyToClipboard(comments) {
        let csvContent = 'Nickname|Date|Comment\n';

        comments.forEach(comment => {
            const nickname = escapeCSV(comment.nickname);
            const date = escapeCSV(comment.date || '');
            const text = escapeCSV(comment.comment);
            csvContent += `${nickname}|${date}|${text}\n`;
        });

        navigator.clipboard.writeText(csvContent).then(() => {
            // Show success message
            const originalText = copyBtn.textContent;
            copyBtn.textContent = '✓ Copied!';
            copyBtn.style.background = '#28a745';
            copyBtn.style.color = 'white';

            setTimeout(() => {
                copyBtn.textContent = originalText;
                copyBtn.style.background = '';
                copyBtn.style.color = '';
            }, 2000);
        }).catch(err => {
            showError('Failed to copy to clipboard');
            console.error('Error:', err);
        });
    }

    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function escapeCSV(text) {
        if (!text) return '';
        // Escape quotes and wrap in quotes if contains special chars
        text = text.replace(/"/g, '""');
        if (text.includes('|') || text.includes('\n') || text.includes('"')) {
            text = `"${text}"`;
        }
        return text;
    }

    function getTimestamp() {
        const now = new Date();
        const year = now.getFullYear();
        const month = String(now.getMonth() + 1).padStart(2, '0');
        const day = String(now.getDate()).padStart(2, '0');
        const hours = String(now.getHours()).padStart(2, '0');
        const minutes = String(now.getMinutes()).padStart(2, '0');
        return `${year}${month}${day}_${hours}${minutes}`;
    }
});
