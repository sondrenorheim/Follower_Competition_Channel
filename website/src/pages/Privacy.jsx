export default function Privacy() {
  return (
    <div className="min-h-screen bg-dark-bg-primary py-16 px-6">
      <div className="max-w-3xl mx-auto">
        <h1 className="text-3xl font-bold text-text-primary mb-8">Privacy Policy</h1>

        <div className="text-text-secondary space-y-6">
          <p>Last updated: January 2026</p>

          <section>
            <h2 className="text-xl font-semibold text-text-primary mb-3">Information We Collect</h2>
            <p>Follower Battlegrounds collects publicly available Instagram usernames and profile pictures of followers who participate in our daily gaming competitions. This information is used solely to create gaming content featuring our community.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-text-primary mb-3">How We Use Your Information</h2>
            <p>We use follower information to:</p>
            <ul className="list-disc list-inside mt-2 space-y-1">
              <li>Create daily gaming videos featuring followers as in-game characters</li>
              <li>Display leaderboards and statistics on our website</li>
              <li>Send automated messages about competition participation</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-text-primary mb-3">Data Retention</h2>
            <p>We retain follower data for as long as you remain a follower of our Instagram account. If you unfollow, your data will be removed from future competitions.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-text-primary mb-3">Your Rights</h2>
            <p>You can request removal of your data at any time by contacting us at followerbattlegrounds@gmail.com or unfollowing our Instagram account.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-text-primary mb-3">Contact Us</h2>
            <p>For privacy-related questions, contact us at: followerbattlegrounds@gmail.com</p>
          </section>
        </div>
      </div>
    </div>
  );
}
