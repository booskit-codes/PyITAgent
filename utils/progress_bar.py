import sys

class ProgressBar:
    def __init__(self, total=100, width=40):
        self.total = total
        self.width = width

    def update_progress(self, progress, description=''):
        completed = int(self.width * progress / self.total)
        bar = '█' * completed + '-' * (self.width - completed)
        # Pad the output with spaces to ensure it clears any remaining text
        padding = ' ' * (self.width - len(description))
        sys.stdout.write(f'\r[{bar}] {progress}% {description}{padding}')
        sys.stdout.flush()

    def finish(self):
        print()
