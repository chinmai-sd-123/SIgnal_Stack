const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function createOutcome(outcome) {
    const response = await fetch(`${API_URL}/outcomes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(outcome),
    });
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || "Failed to create outcome");
    }
    return response.json();
}

// === JOB API ===
export async function createJob(job) {
    const response = await fetch(`${API_URL}/jobs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(job),
    });
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || "Failed to create job");
    }
    return response.json();
}

export async function updateJobStatus(jobId, status) {
    const response = await fetch(`${API_URL}/jobs/${jobId}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status })
    });
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to update job status');
    }
    return response.json();
}

// ============================================================================
// SHORTLIST API FUNCTIONS
// ============================================================================

// Update candidate status (shortlisted/rejected)
export async function updateCandidateStatus(jobId, candidateId, status) {
    const response = await fetch(`${API_URL}/jobs/${jobId}/candidates/${candidateId}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status })  // "shortlisted" | "rejected"
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to update candidate status');
    }

    return response.json();
}

// Shortlist management
export async function getShortlist(jobId, autoSelect = false) {
    const response = await fetch(`${API_URL}/jobs/${jobId}/shortlist?auto_select=${autoSelect}`);
    if (!response.ok) throw new Error('Failed to get shortlist');
    return response.json();
}

export async function updateShortlist(jobId, candidateIds) {
    const response = await fetch(`${API_URL}/jobs/${jobId}/shortlist`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ candidate_ids: candidateIds })
    });
    if (!response.ok) throw new Error('Failed to update shortlist');
    return response.json();
}

export async function finalizeShortlist(jobId) {
    const response = await fetch(`${API_URL}/jobs/${jobId}/finalize-shortlist`, {
        method: 'POST'
    });
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to finalize shortlist');
    }
    return response.json();
}

export async function archiveJob(jobId) {
    const response = await fetch(`${API_URL}/jobs/${jobId}/archive`, {
        method: 'PATCH'
    });
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to archive job');
    }
    return response.json();
}

export async function getJobs() {
    // Fetch all jobs including archived, we'll filter on client side
    const response = await fetch(`${API_URL}/jobs?include_archived=true`);
    if (!response.ok) throw new Error("Failed to fetch jobs");
    return response.json();
}

export async function getJob(jobId) {
    const response = await fetch(`${API_URL}/jobs/${jobId}`);
    if (!response.ok) throw new Error("Failed to fetch job");
    return response.json();
}

export async function getJobOutcomes(jobId) {
    const response = await fetch(`${API_URL}/jobs/${jobId}/outcomes`);
    if (!response.ok) throw new Error("Failed to fetch job outcomes");
    return response.json();
}

// === OUTCOME API ===
export async function getOutcome(outcomeId) {
    const response = await fetch(`${API_URL}/outcomes/${outcomeId}`);
    if (!response.ok) throw new Error("Failed to fetch outcome");
    return response.json();
}

// Mock function to get all outcomes (since backend doesn't have list endpoint yet)
// In a real app, we would add GET /outcomes
export async function getOutcomes() {
    // For MVP demo, we can just return a list if we had one, or fetch known ones.
    // Since we don't have a list endpoint, we'll mock it or add it to backend.
    // Let's add it to backend for correctness.
    const response = await fetch(`${API_URL}/outcomes`);
    if (!response.ok) return []; // Return empty if endpoint missing
    return response.json();
}

export async function getOutcomeTemplates(categorySlug = null) {
    const url = categorySlug
        ? `${API_URL}/outcome-templates?category_slug=${categorySlug}`
        : `${API_URL}/outcome-templates`;
    const response = await fetch(url);
    if (!response.ok) return [];
    return response.json();
}

export async function deleteJob(jobId, hardDelete = false) {
    const url = `${API_URL}/jobs/${jobId}${hardDelete ? '?hard_delete=true' : ''}`;
    const response = await fetch(url, {
        method: 'DELETE',
    });
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to delete job');
    }
    return response.json();
}

export async function submitProof(proof) {
    const response = await fetch(`${API_URL}/proofs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(proof),
    });
    if (!response.ok) throw new Error("Failed to trigger evaluation");
    return response.json();
}

export async function submitFeedback(feedback) {
    const response = await fetch(`${API_URL}/plugin/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(feedback),
    });
    return response.json();
}

export async function submitTaskFeedback(feedback) {
    const response = await fetch(`${API_URL}/feedback/task-weight`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(feedback),
    });
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || "Failed to submit task feedback");
    }
    return response.json();
}

export async function getSignalWeights() {
    const response = await fetch(`${API_URL}/admin/signal-weights`);
    return response.json();
}

export async function resetDecision(jobId) {
    const response = await fetch(`${API_URL}/feedback/reset/${jobId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
    });
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || "Failed to reset decision");
    }
    return response.json();
}

export async function getEvaluations() {
    const response = await fetch(`${API_URL}/evaluations`);
    if (!response.ok) throw new Error("Failed to fetch evaluations");
    return response.json();
}

export async function getProofs(outcomeId) {
    const response = await fetch(`${API_URL}/proofs/${outcomeId}`);
    if (!response.ok) throw new Error("Failed to fetch proofs");
    return response.json();
}

export async function triggerEvaluation(payload) {
    const response = await fetch(`${API_URL}/plugin/evaluate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error("Failed to trigger evaluation");
    return response.json();
}

export async function getEvaluation(jobId) {
    const response = await fetch(`${API_URL}/plugin/status/${jobId}`);
    if (!response.ok) throw new Error("Failed to fetch evaluation");
    const data = await response.json();
    // Return the whole object so the UI can check status
    return data;
}

export const suggestTasks = async (description) => {
    const response = await fetch(`${API_URL}/plugin/suggest-tasks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ description })
    });
    if (!response.ok) throw new Error('Failed to suggest tasks');
    return response.json();
};

export const getRepoPreview = async (repoUrl) => {
    const response = await fetch(`${API_URL}/plugin/repo-preview?repo_url=${encodeURIComponent(repoUrl)}`);
    if (!response.ok) throw new Error('Failed to fetch repo preview');
    return response.json();
};

export const getLeetCodeStats = async (username) => {
    const response = await fetch(`${API_URL}/plugin/leetcode/${username}`);
    if (!response.ok) throw new Error('Failed to fetch leetcode stats');
    return response.json();
};

export async function getAuditLogs() {
    const response = await fetch(`${API_URL}/admin/audit-logs`);
    if (!response.ok) throw new Error("Failed to fetch audit logs");
    return response.json();
}

export async function getGithubRepos(username, jobId) {
    const response = await fetch(`${API_URL}/plugin/github/repos/select`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ github_username: username, job_id: jobId })
    });
    if (response.ok) {
        const data = await response.json();
        if (Array.isArray(data) && data.length > 0) {
            return data;
        }
    } else {
        const errorData = await response.json().catch(() => ({}));
        console.warn("Backend repo selector failed", errorData);
    }

    // Fallback to GitHub public API for basic repo listing.
    const ghResponse = await fetch(`https://api.github.com/users/${encodeURIComponent(username)}/repos?per_page=30&sort=updated`);
    if (!ghResponse.ok) {
        throw new Error('Failed to fetch repos');
    }
    const repos = await ghResponse.json();
    return repos.map((repo) => ({
        owner: repo.owner?.login || '',
        repo: repo.name || '',
        url: repo.html_url || '',
        score: 0,
        manifest_present: false,
        language: repo.language || null,
        last_commit_date: repo.pushed_at || null,
        size_kb: repo.size || 0,
        breakdown: {
            name_match: 0,
            manifest: 0,
            recency: 0,
            size: 0,
            language_match: 0,
        },
    }));
}

export async function saveTasksBatch(payload) {
    const response = await fetch(`${API_URL}/tasks/batch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || "Failed to save tasks");
    }
    return response.json();
}


export async function getHiringHistory() {
    const response = await fetch(`${API_URL}/analytics/decisions`);
    if (!response.ok) throw new Error("Failed to fetch hiring history");
    return response.json();
}

export async function getAnalyticsMetrics() {
    const response = await fetch(`${API_URL}/analytics/metrics`);
    if (!response.ok) throw new Error("Failed to fetch analytics metrics");
    return response.json();
}
